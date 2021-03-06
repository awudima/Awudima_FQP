
from awudima.pyrml import TermMap, TripleMapType, TermType
from awudima.pysparql import Argument

from awudima.sql.lang.model import SQLColumn, SQLCondition, SQLAndCondition, SQLSelectExpression, SQLFunction


class TermMap2SQL:
    """
    Translates rr:TermMap to SQL expression.
    rr:TermMap is A function that generates an RDF term from a logical table row.
    The URI of this class is http://www.w3.org/ns/r2rml#TermMap

    rml.io:
    An RDF term is either an IRI, or a blank node, or a literal.
    A term map is a function that generates an RDF term from a logical reference.
    The result of that function is known as the term map's generated RDF term.

    Term maps are used to generate the subjects, predicates and objects of the RDF triples that
     are generated by a triples map. Consequently, there are several kinds of term maps, depending
     on where in the mapping they occur: subject maps, predicate maps, object maps and graph maps.

    A term map must be exactly one of the following:
        - a constant-valued term map,
        - a reference-valued term map,
        - a template-valued term map.

    The references of a term map are the set of logical references referenced in the
    term map and depend on the type of term map.
    """

    def __init__(self,
                 term_map: TermMap,
                 rdf_term: Argument,
                 comparision_opr='=',
                 table_alias=None,
                 schema=None):
        self.term_map = term_map
        self.rdf_term = rdf_term
        self.projection = None
        self.filter_conditions = None
        self.schema = schema
        self.table_alias = table_alias

        self.comparision_opr = comparision_opr
        self.sparql_result_template = dict()
        self.term = None

        self._process_term_map()

    def _process_term_map(self):
        """
        If the rdf_term is constant, then extract filter conditions but there will not be any projections
        Otherwise, project the term's mapping column/item and make sure the values are bound (not null or empty)
        Called when this object is init or either of its property (term_map/rdf_term) are updated
        using setter methods defined below

        :return:
        """
        term, result_json_template = TermMap2SQL.get_sql_term(self.term_map, self.table_alias, self.schema)
        self.term = term
        self.sparql_result_template = result_json_template

        if self.rdf_term.constant:
            self.filter_conditions = self.get_filter_condition()
            self.sparql_result_template = dict()  # self.rdf_term.name
            self.projection = None
        else:
            self.filter_conditions = self.get_bound_columns()
            self.projection = self.get_projections()

    def get_projections(self):
        """
        extracts SQL projection variables from RDF Term. If the term is a variable,
        returns an SQLSelectExpression else None

        :return: SQLSelectExpression object if the rdf_term is a variable, else None
        """
        if self.rdf_term.constant:
            return None
        rdf_term_var = self.rdf_term.name

        if self.term is not None:
            proj = SQLSelectExpression(self.term, rdf_term_var[1:])

        else:
            proj = None
        return proj

    @staticmethod
    def get_expr(expressions):
        expr = []
        for template in expressions:
            if len(template) > 1:
                if len(template[0]) > 0:
                    # it is a constant string and column name
                    expr.append("'" + template[0] + "'")
                    expr.append('`' + template[1] + '`')
                else:
                    # it is empty separator and column name.
                    # in this case only the column name will be concatenated
                    expr.append('`' + template[1] + '`')
            elif len(template) == 1:
                # else it is a constant string
                expr.append("'" + template[0] + "'")
        return expr

    def get_bound_columns(self):
        """
        Prepares an SQL query to make sure that a column is NOT NULL. When translating conjunctive SPARQL queries,
        every column should be bounded (not NULL). This translation assumes no optional columns (OPTIONAL clause) is
        considered in the SPARQL query, ONLY BGPs (basic graph patterns), i.e., TriplePatterns and Filter expressions.

        :return: SQLAndCondition object representing all columns involved in creating the RDF Term (a variable)
                or empty list if rdf_term is constant. Checking constant mappings are done as filter_conditions()
        """
        if self.rdf_term.constant:
            return None
        sql_conditions = [SQLCondition(SQLColumn(column, self.table_alias, self.schema), ' IS NOT ', 'NULL')
                          for column in self.term_map.columns]
        return SQLAndCondition(sql_conditions)

    @staticmethod
    def get_sql_term(term_map, table_alias=None, schema=None):
        """
        A utility method that translates an RML term map (rr:TermMap) into an SQL query expression of a Column or Function.

        :param term_map: An RML term map (rr:TermMap)
        :param table_alias: table alias
        :param schema: schema or database name

        :return: a two-element tuple containing an SQLColumn/SQLFunction and SPARQLJSONResult representation.
              An SQL column (SQLColumn) or function (SQLFunction) expression is translation of the given rr:TermMap
        """
        term = None
        result_json_template = dict()
        if term_map.resource_type == TripleMapType.TEMPLATE:
            # split the template as [[const_string_1, column_name_1], ... ]
            # this will be WHERE concat(const_string_1, column_name_1, ...) = rdf_term_value
            temp_split = term_map.split_template()
            if len(temp_split) > 0:
                # if term_type is BNode then prepend _:
                if term_map.term_type == TermType.BNode:
                    temp_split[0][0] = '_:' + temp_split[0][0]
                    result_json_template['type'] = 'bnode'
                expr = TermMap2SQL.get_expr(temp_split)
                if len(expr) > 1:
                    cols = [SQLColumn('`' + column + '`', table_alias, schema) for column in term_map.columns]
                    term = SQLFunction('CONCAT', expr, columns=cols)
                else:
                    term = SQLColumn(expr[0], table_alias, schema)
            if 'type' not in result_json_template:
                result_json_template['type'] = 'uri'
            result_json_template['value'] = ''
        elif term_map.resource_type == TripleMapType.REFERENCE:
            # if term is a reference to a single column, then we check the value as is
            if term_map.term_type == TermType.BNode:
                # filter_conditions.append(([['_:', self.term_map.value]], '=', rdf_term_value))
                expr = TermMap2SQL.get_expr([['_:', term_map.value]])
                if len(expr) > 1:
                    cols = [SQLColumn('`' + column + '`', table_alias, schema) for column in term_map.columns]
                    term = SQLFunction('CONCAT', expr, columns=cols)
                else:
                    term = SQLColumn(expr[0], table_alias, schema)
                result_json_template['type'] = 'bnode'
                result_json_template['value'] = ''
            elif term_map.term_type == TermType.IRI:
                term = SQLColumn(term_map.value, table_alias, schema)
                result_json_template['type'] = 'uri'
                result_json_template['value'] = ''
            else:
                # term_map.value in this case is a column name (table variable)
                # filter_conditions.append((self.term_map.value, '=', rdf_term_value))
                term = SQLColumn(term_map.value, table_alias, schema)
                result_json_template['type'] = 'literal'
                result_json_template['value'] = ''
        else:
            # if term is constant, then we just check the value as constant
            # WHERE rml_term_map.value = rdf_term_value
            # term_map.value in this case is a constant value
            # TODO: this should be used as early stopping condition since both operands are constant values
            # filter_conditions.append(([[self.term_map.value]], '=', rdf_term_value))
            # term = SQLColumn(term_map.value, table_alias, schema)

            result_json_template['value'] = term_map.value
            if term_map.term_type == TermType.BNode:
                result_json_template['type'] = 'bnode'
            elif term_map.term_type == TermType.Literal:
                result_json_template['type'] = 'literal'
            else:
                result_json_template['type'] = 'uri'

        return term, result_json_template

    def get_filter_condition(self):
        """
        Get an SQLCondition representation of a constant RDF Term.

        :return: - SQLCondition representation or None if the RDF Term value and RML Term map have same value.
                 - empty list if rdf_term is not constant
        """
        if not self.rdf_term.constant:
            return None

        rdf_term_value = self.rdf_term.name
        if self.term_map.term_type != TermType.BNode:
            if rdf_term_value[0] in ['"', '<', "'"]:
                rdf_term_value = "'" + rdf_term_value[1:-1] + "'"
            else:
                rdf_term_value = "'" + rdf_term_value + "'"

        if self.term is not None:
            # if the term map is not a constant term and rdf_term is constant
            sql_filter = SQLAndCondition([SQLCondition(self.term, str(self.comparision_opr), rdf_term_value)])
        else:
            if self.comparision_opr == '=':
                if self.sparql_result_template['value'] == rdf_term_value:
                    sql_filter = None
                else:
                    sql_filter = SQLAndCondition([SQLCondition(False)])

            else:
                sql_filter = SQLAndCondition([SQLCondition("'" + self.sparql_result_template['value'] + "'",
                                                           str(self.comparision_opr), rdf_term_value)])
        return sql_filter


if __name__ == "__main__":
    from awudima.pyrml import TermMap, TermType
    from awudima.pysparql import Argument
    from pprint import pprint

    tm = TermMap('name', TripleMapType.REFERENCE, TermType.Literal)
    v = Argument("?nvar", False)
    sqlv = TermMap2SQL(tm, v)
    print('TermMap:', tm)
    print('RDF_Term:', v)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:', sqlv.sparql_result_template)
    print("----------------------")
    c = Argument('"Addis Ababa"', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:', sqlv.sparql_result_template)
    print("----------------------")
    c = Argument('Addis Ababa', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")
    print("===============================")
    # TEMPLATE
    tm = TermMap('http://hello.us/City/{name}', TripleMapType.TEMPLATE, TermType.IRI)
    v = Argument("?nvar", False)
    sqlv = TermMap2SQL(tm, v)
    print('TermMap:', tm)
    print('RDF_Term:', v)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")

    c = Argument('<http://hello.us/City/Addis%20Ababa>', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")
    print("===============================")
    # BNODE
    tm = TermMap('http://hello.us/City/{name}', TripleMapType.TEMPLATE, TermType.BNode)
    v = Argument("?nvar", False)
    sqlv = TermMap2SQL(tm, v)
    print('TermMap:', tm)
    print('RDF_Term:', v)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")

    c = Argument('_:http://hello.us/City/Addis%20Ababa', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")
    print("===============================")
    # CONSTANT Literal Term
    tm = TermMap('Addis Ababa', TripleMapType.CONSTANT, TermType.Literal)
    v = Argument("?nvar", False)
    sqlv = TermMap2SQL(tm, v)
    print('TermMap:', tm)
    print('RDF_Term:', v)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")

    c = Argument('"Addis Ababa"', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("===================================")
    # CONSTANT IRI Term
    tm = TermMap('http://hello.us/City/Addis%20Ababa', TripleMapType.CONSTANT, TermType.IRI)
    v = Argument("?nvar", False)
    sqlv = TermMap2SQL(tm, v)
    print('TermMap:', tm)
    print('RDF_Term:', v)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("----------------------")

    c = Argument('<http://hello.us/City/Addis%20Ababa>', True)
    sqlv = TermMap2SQL(tm, c)
    print('TermMap:', tm)
    print('RDF_Term:', c)
    pprint(sqlv.term)
    print('projection:', sqlv.projection, ', filter:', sqlv.filter_conditions, ', template:',
          sqlv.sparql_result_template)
    print("===============================")