
__author__ = 'Kemele M. Endris'

from typing import List, Dict

xsd = "http://www.w3.org/2001/XMLSchema#"


class SPARQL:

    @staticmethod
    def readGeneralPredicates(fileName):

        f = open(fileName, 'r')
        l = []
        l0 = f.readline()
        while not l0 == '':
            l0 = l0.rstrip('\n')
            l.append(l0)
            l0 = f.readline()
        f.close()
        return l

    @staticmethod
    def getUri(p, prefs):
        prefs.update({
            'rdfs': "<http://www.w3.org/2000/01/rdf-schema#>",
            'owl': "<http://www.w3.org/2002/07/owl#>",
            'rdf': "<http://www.w3.org/1999/02/22-rdf-syntax-ns#>"
        })
        if p.datatype or p.lang:
            return p.name + ("^^" + p.datatype if p.datatype else "") + ("@" + p.lang if p.lang else "")
        if "'" in p.name or '"' in p.name:
            return p.name
        hasPrefix = SPARQL.prefix(p)
        if hasPrefix:
            (pr, su) = hasPrefix
            n = prefs[pr]
            n = n[:-1] + su + ">"
            return n
        return p.name

    @staticmethod
    def prefix(p):
        s = p.name
        pos = s.find(":")
        if (not (s[0] == "<")) and pos > -1:
            return s[0:pos].strip(), s[(pos + 1):].strip()

        return None

    @staticmethod
    def getVars(sg):

        s = []
        if not sg.subject.constant:
            s.append(sg.subject.name)
        if not sg.theobject.constant:
            s.append(sg.theobject.name)
        return s

    @staticmethod
    def getPrefs(ps):
        prefDict = dict()
        for p in ps:
            pos = p.find(":")
            c = p[0:pos].strip()
            v = p[(pos + 1):len(p)].strip()
            prefDict[c] = v
        return prefDict

    @staticmethod
    def getFilterVarsUnionBlock(ub):
        filter_vars = []
        if len(ub.filters) > 0:
            for f in ub.filters:
                filter_vars.extend(f.getVars())

        for jb in ub.triples:
            filter_vars.extend(SPARQL.getFilterVarsJoinBlock(jb))

        return filter_vars

    @staticmethod
    def getFilterVarsJoinBlock(jb):

        join_vars = []
        if len(jb.filters) > 0:
            for f in jb.filters:
                join_vars.extend(f.getVars())

        if isinstance(jb, JoinBlock) and isinstance(jb.triples, list):

            for bgp in jb.triples:
                if isinstance(bgp, Service):
                    join_vars.extend(SPARQL.getFilterVarsUnionBlock(bgp.triples))
                elif isinstance(bgp, Optional):
                    join_vars.extend(SPARQL.getFilterVarsUnionBlock(bgp.bgg))
                elif isinstance(bgp, UnionBlock):
                    join_vars.extend(SPARQL.getFilterVarsUnionBlock(bgp))
                elif isinstance(bgp, JoinBlock):
                    join_vars.extend(SPARQL.getFilterVarsJoinBlock(bgp))
        return join_vars

    @staticmethod
    def getUnionBlockVars(ub):
        variables = []
        for jb in ub.triples:
            variables.extend(SPARQL.getJoinBlockVars(jb))

        return list(set(variables))

    @staticmethod
    def getJoinBlockVars(jb):
        join_vars = []
        for bgp in jb.triples:
            if isinstance(bgp, Triple):
                join_vars.extend(bgp.getVars())
            elif isinstance(bgp, Service):
                join_vars.extend(bgp.getVars())
            elif isinstance(bgp, Optional):
                join_vars.extend(bgp.getVars())
            elif isinstance(bgp, UnionBlock):
                join_vars.extend(SPARQL.getUnionBlockVars(bgp))
            elif isinstance(bgp, JoinBlock):
                join_vars.extend(SPARQL.getJoinBlockVars(bgp))
        return join_vars

    @staticmethod
    def getQueryVars(ub):
        return SPARQL.getUnionBlockVars(ub)

    @staticmethod
    def getJoinVarsUnionBlock(ub):
        join_vars = []

        for jb in ub.triples:
            join_vars.extend(SPARQL.getJoinVarsJoinBlock(jb))

        return join_vars

    @staticmethod
    def getJoinVarsJoinBlock(jb):

        join_vars = []

        for bgp in jb.triples:

            if isinstance(bgp, Triple):
                if not bgp.subject.constant:
                    join_vars.append(bgp.subject.name)
                if not bgp.theobject.constant:
                    join_vars.append(bgp.theobject.name)
            elif isinstance(bgp, Service):
                join_vars.extend(SPARQL.getJoinVarsUnionBlock(bgp.triples))
            elif isinstance(bgp, Optional):
                join_vars.extend(SPARQL.getJoinVarsUnionBlock(bgp.bgg))
            elif isinstance(bgp, UnionBlock):
                join_vars.extend(SPARQL.getJoinVarsUnionBlock(bgp))
            elif isinstance(bgp, JoinBlock):
                join_vars.extend(SPARQL.getJoinVarsJoinBlock(bgp))
        return join_vars

    @staticmethod
    def aux(e, x, op):

        def pp(t):
            return t.show(x + "  ")

        if type(e) == tuple:
            (f, s) = e
            r = ""
            if f:
                r = x + "{\n" + SPARQL.aux(f, x + "  ", op) + "\n" + x + "}\n"
            if f and s:
                r = r + x + op + "\n"
            if s:
                r = r + x + "{\n" + SPARQL.aux(s, x + "  ", op) + "\n" + x + "}"
            return r
        elif type(e) == list:
            return (x + " . \n").join(map(pp, e))
        elif e:
            return e.show(x + "  ")

        return ""

    @staticmethod
    def aux2(e, x, op):
        def pp(t):
            return t.show2(x + "  ")

        if type(e) == tuple:
            (f, s) = e
            r = ""
            if f:
                r = x + "{\n" + SPARQL.aux2(f, x + "  ", op) + "\n" + x + "}\n"
            if f and s:
                r = r + x + op + "\n"
            if s:
                r = r + x + "{\n" + SPARQL.aux2(s, x + "  ", op) + "\n" + x + "}"
            return r
        elif type(e) == list:
            return (x + " . \n").join(map(pp, e))
        elif e:
            return e.show2(x + "  ")
        return ""

    @staticmethod
    def nest(l):

        l0 = list(l)
        while len(l0) > 1:
            l1 = []
            while len(l0) > 1:
                x = l0.pop()
                y = l0.pop()
                l1.append((x, y))
            if len(l0) == 1:
                l1.append(l0.pop())
            l0 = l1
        if len(l0) == 1:
            return l0[0]
        else:
            return None

    unaryFunctor = {
        '!',
        'BOUND',
        'bound',
        'ISIRI',
        'isiri',
        'ISURI',
        'isuri',
        'ISBLANK',
        'isblank',
        'ISLITERAL',
        'isliteral',
        'STR',
        'str',
        'UCASE',
        'ucase',
        'LANG',
        'lang',
        'DATATYPE',
        'datatype',
        'xsd:double',
        'xsd:integer',
        'xsd:decimal',
        'xsd:float',
        'xsd:string',
        'xsd:boolean',
        'xsd:dateTime',
        'xsd:nonPositiveInteger',
        'xsd:negativeInteger',
        'xsd:long',
        'xsd:int',
        'xsd:short',
        'xsd:byte',
        'xsd:nonNegativeInteger',
        'xsd:unsignedInt',
        'xsd:unsignedShort',
        'xsd:unsignedByte',
        'xsd:positiveInteger',
        '<http://www.w3.org/2001/XMLSchema#integer>',
        '<http://www.w3.org/2001/XMLSchema#decimal>',
        '<http://www.w3.org/2001/XMLSchema#double>',
        '<http://www.w3.org/2001/XMLSchema#float>',
        '<http://www.w3.org/2001/XMLSchema#string>',
        '<http://www.w3.org/2001/XMLSchema#boolean>',
        '<http://www.w3.org/2001/XMLSchema#dateTime>',
        '<http://www.w3.org/2001/XMLSchema#nonPositiveInteger>',
        '<http://www.w3.org/2001/XMLSchema#negativeInteger>',
        '<http://www.w3.org/2001/XMLSchema#long>',
        '<http://www.w3.org/2001/XMLSchema#int>',
        '<http://www.w3.org/2001/XMLSchema#short>',
        '<http://www.w3.org/2001/XMLSchema#byte>',
        '<http://www.w3.org/2001/XMLSchema#nonNegativeInteger>',
        '<http://www.w3.org/2001/XMLSchema#unsignedInt>',
        '<http://www.w3.org/2001/XMLSchema#unsignedShort>',
        '<http://www.w3.org/2001/XMLSchema#unsignedByte>',
        '<http://www.w3.org/2001/XMLSchema#positiveInteger>'
    }

    binaryFunctor = {
        'REGEX',
        'SAMETERM',
        'LANGMATCHES',
        'CONTAINS',
        'langMatches',
        'regex',
        'sameTerm'
    }


class Query(object):

    def __init__(self, prefs, args, body, distinct, order_by: List = None, limit=-1, offset=-1, filter_nested='', qtype=0):
        self.prefs = prefs
        self.args = args
        self.body = body
        self.distinct = distinct
        self.join_vars = self.getJoinVars()
        self.order_by = order_by
        if self.order_by is None:
            self.order_by = []
        self.limit = limit
        self.offset = offset
        self.query_type = qtype
        if self.query_type == 2:
            self.limit = 1
        self.filter_nested = filter_nested
        genPred = [] #readGeneralPredicates('ontario/common/parser/generalPredicates')
        self.body.setGeneral(SPARQL.getPrefs(self.prefs), genPred)

    def __repr__(self):
        body_str = str(self.body)
        return self._show(body_str)

    def instantiate(self, d):
        new_args = []
        # for a in self.args:
        #     an = string.lstrip(string.lstrip(self.subject.name, "?"), "$")
        #     if not (an in d):
        #         new_args.append(a)
        # return Query(self.prefs, new_args, self.body.instantiate(d), self.distinct)
        self.body = self.body.instantiate(d)
        return self

    def instantiateFilter(self, d, filter_str):
        new_args = []
        # for a in self.args:
        #     an = string.lstrip(string.lstrip(self.subject.name, "?"), "$")
        #     if not (an in d):
        #         new_args.append(a)
        # return Query(self.prefs, new_args, self.body, self.distinct, self.filter_nested + ' ' + filter_str)
        self.body = self.body.instantiate(d)
        self.filter_nested += ' ' + filter_str
        return self

    def places(self):
        return self.body.places()

    def constantNumber(self):
        return self.body.constantNumber()

    def constantPercentage(self):
        return self.constantNumber()/self.places()

    def show(self):

        body_str = self.body.show(" ")
        return self._show(body_str)

    def show2(self):

        body_str = self.body.show2(" ")
        return self._show(body_str)

    def _show(self, body_str):
        d = ""
        if self.query_type == 0:
            qtype = "SELECT"
            if len(self.args) == 0:
                args_str = "*"
            else:
                args_str = " ".join(map(str, self.args))

            args_str += "\n"
            if self.distinct is not None and self.distinct:
                d = "DISTINCT "
            return self.getPrefixes() + qtype + " " + d + args_str + " WHERE {" + body_str + "\n" + self.filter_nested + "\n}"

        elif self.query_type == 1:
            qtype = "CONSTRUCT"
            args_str = "\n".join(map(str, self.args))
            return self.getPrefixes() + qtype + " {" + args_str + "\n}\nWHERE {" + body_str + "\n" + self.filter_nested + "\n}"
        else:
            qtype = "ASK"
            return self.getPrefixes() + qtype + " " + " WHERE {" + body_str + "\n" + self.filter_nested + "\n}"

    def getPrefixes(self):
        r = ""
        for e in self.prefs:
            i = e.find(":")
            e = e[:i] + ": " + e[i+1:]
            r = r + "\nprefix "+e
        if not r == "":
            r = r + "\n"
        return r

    def getJoinVars(self):

        join_vars = SPARQL.getJoinVarsUnionBlock(self.body)
        join_vars = [v for v in join_vars if join_vars.count(v) > 1]

        return set(join_vars)

    def getFilterVars(self):
        filtervars = SPARQL.getFilterVarsUnionBlock(self.body)

        return set(filtervars)

    def getJoinVars2(self):

        join_vars = []

        for s in self.body:
            for t in s.triples:
                if not t.subject.constant:
                    join_vars.append(t.subject.name)
                if not t.theobject.constant:
                    join_vars.append(t.theobject.name)

        join_vars = [v for v in join_vars if join_vars.count(v) > 1]

        return set(join_vars)

    def getVars(self):
        return SPARQL.getQueryVars(self.body)

    def getTreeRepresentation(self):

        l0 = self.body
        while len(l0) > 1:
            l1 = []
            while len(l0) > 1:
                x = l0.pop()
                y = l0.pop()
                l1.append((x, y))
            if len(l0) == 1:
                l1.append(l0.pop())
            l0 = l1
        if len(l0) == 1:
            return SPARQL.aux(l0[0], "", " xxx ")
        else:
            return " "


class Service(object):

    def __init__(self,
                 endpoint,
                 triples,
                 datasource,
                 rdfmts: List,
                 stars: Dict,
                 filters: List,
                 star_filters: Dict,
                 limit: int = -1,
                 filter_nested: List = None):

        self.endpoint = endpoint
        self.triples = triples
        self.filters = filters
        if filter_nested is None:
            filter_nested = []
        self.filter_nested = filter_nested# TODO: this is used to store the filters from NestedLoop operators
        self.limit = limit  # TODO: This arg was added in order to integrate contactSource with incremental calls (16/12/2013)

        self.datasource = datasource
        if rdfmts is None:
            rdfmts = []
        self.rdfmts = rdfmts
        self.stars = stars
        self.star_filters = star_filters
        self.translated_query = None

    def include_filter(self, f):
        self.filters.append(f)

    def __add__(self, other):
        self.triples.extend(other.triples)
        self.filters.extend(other.filters)
        self.filter_nested.extend(other.filter_nested)
        if other.limit > self.limit:
            self.limit = other.limit

    def __repr__(self):
        if isinstance(self.triples, list):
            triples_str = " . ".join(map(str, self.triples))
        else:
            triples_str = str(self.triples)
        filters_str = " . ".join(map(str, self.filters)) + " \n".join(map(str, self.filter_nested))
        return (" { SERVICE <" + self.endpoint + "> { "
                + triples_str + filters_str + " }   \n }")

    def __lt__(self, other):
        """
        compares two triples patterns based on the position of contants
        :param other:
        :return:
        """
        if other.const_subjects() + other.const_predicates() > self.const_subjects() + self.const_predicates():
            return False
        elif other.const_subjects() + other.const_predicates() < self.const_subjects() + self.const_predicates():
            return True
        elif other.const_subjects() > self.const_subjects():
            return False
        elif other.const_subjects() < self.const_subjects():
            return True
        elif other.const_objects() + other.const_predicates() > self.const_objects() + self.const_predicates():
            return False
        elif other.const_objects() + other.const_predicates() < self.const_objects() + self.const_predicates():
            return True
        elif other.const_objects() > self.const_objects():
            return False
        elif other.const_objects() < self.const_objects():
            return True
        elif other.const_subjects() == self.const_subjects():
            if other.const_predicates() > self.const_predicates():
                return False
            elif other.const_predicates() < self.const_predicates():
                return True
            elif other.const_objects() > self.const_objects():
                return False
            elif other.const_objects() < self.const_objects():
                return True
        if other.constantPercentage() == self.constantPercentage():
            if other.constantNumber() > self.constantNumber():
                return False
            else:
                return True

        return self.constantPercentage() > other.constantPercentage()

    def allTriplesGeneral(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesGeneral()
        else:
            a = self.triples.allTriplesGeneral()
        return a

    def allTriplesLowSelectivity(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesLowSelectivity()
        else:
            a = self.triples.allTriplesLowSelectivity()
        a = a or (self.filters != [])
        return a

    def instantiate(self, d):
        if isinstance(self.triples, list):
            new_triples = [t.instantiate(d) for t in self.triples]
        else:
            new_triples = self.triples.instantiate(d)

        self.triples = new_triples
        # return Service("<"+self.endpoint+">", new_triples, self.limit)
        return self

    def instantiateFilter(self, d, filter_str):
        new_filters = []
        # new_filters.extend(self.filter_nested)
        new_filters.append(filter_str)
        #new_filters_vars = self.filters_vars | set(d)
        self.filter_nested = new_filters

        return self
        # Service("<"+self.endpoint+">", self.triples,
        #                limit=self.limit, filter_nested=new_filters,
        #                datasource=self.datasource, rdfmts=self.rdfmts,
        #                star=self.star)

    def getTriples(self):
        if isinstance(self.triples, list):
            triples_str = " . ".join(map(str, self.triples))
        else:
            triples_str = str(self.triples)
        return triples_str + " . ".join(map(str, self.filters)) + " . ".join(map(str, self.filter_nested))

    def show(self, x):
        if self.translated_query is not None:
            return (x + "SERVICE <" + self.endpoint + "> { \n" + self.translated_query
                    + "\n" + x + "}")

        def pp(t):
            if isinstance(t, str):
                return ""
            return t.show(x + "    ")
        if isinstance(self.triples, list):
            triples_str = " . \n".join(map(pp, self.triples))
        else:
            triples_str = self.triples.show(x + "    ")
        filters_str = " . \n".join(map(pp, self.filters)) + "  \n".join(map(pp, self.filter_nested))

        return (x + "SERVICE <" + self.endpoint + "> { \n" + triples_str
                + filters_str + "\n" + x + "}")

    def show2(self, x):
        def pp(t):
            return t.show2(x + "    ")
        if isinstance(self.triples, list):
            triples_str = " . \n".join(map(pp, self.triples))
        else:
            triples_str = self.triples.show2(x + "    ")
        filters_str = " . \n".join(map(pp, self.filters)) + "  \n".join(map(pp, self.filter_nested))
        return triples_str + filters_str

    def getVars(self):
        if isinstance(self.triples, list):
            l = []
            for t in self.triples:
                l = l + t.getVars()
        else:
            l = self.triples.getVars()
        return l

    def getConsts(self):
        if isinstance(self.triples, list):
            c = []
            for t in self.triples:
                c = c + t.getConsts()
        else:
            c = self.triples.getConsts()

        return c

    def getPredVars(self):
        if isinstance(self.triples, list):
            l = []
            for t in self.triples:
                l = l + t.getPredVars()
        else:
            l = self.triples.getPredVars()
        return l

    def places(self):
        p = 0
        if isinstance(self.triples, list):
            for t in self.triples:
                p = p + t.places()
        else:
            p = self.triples.places()
        return p

    def constantNumber(self):
        p = 0
        if isinstance(self.triples, list):
            for t in self.triples:
                p = p + t.constantNumber()
        else:
            p = self.triples.constantNumber()
        return p

    def const_subjects(self):
        p = 0
        if isinstance(self.triples, list):
            for t in self.triples:
                p = p + t.const_subjects()
        else:
            p = self.triples.const_subjects()
        return p

    def const_objects(self):
        p = 0
        if isinstance(self.triples, list):
            for t in self.triples:
                p = p + t.const_objects()
        else:
            p = self.triples.const_objects()
        return p

    def const_predicates(self):
        p = 0
        if isinstance(self.triples, list):
            for t in self.triples:
                p = p + t.const_predicates()
        else:
            p = self.triples.const_predicates()
        return p

    def constantPercentage(self):
        if self.places() == 0:
            return 0
        return self.constantNumber()/self.places()

    def setGeneral(self, ps, genPred):
        if isinstance(self.triples, list):
            for t in self.triples:
                t.setGeneral(ps, genPred)
        else:
            self.triples.setGeneral(ps, genPred)


class UnionBlock(object):
    def __init__(self, triples, filters: List = None):
        self.triples = triples
        self.filters = filters
        if self.filters is None:
            self.filters = []

    def __repr__(self):
        return self.show(" ")

    def show(self, w):

        n = SPARQL.nest(self.triples)

        if n is not None:
            return SPARQL.aux(n, w, " UNION ") + " ".join(map(str, self.filters))
        else:
            return " "

    def setGeneral(self, ps, genPred):
        if isinstance(self.triples, list):
            for t in self.triples:
                t.setGeneral(ps, genPred)
        else:
            self.triples.setGeneral(ps, genPred)

    def allTriplesGeneral(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesGeneral()
        else:
            a = self.triples.allTriplesGeneral()
        return a

    def allTriplesLowSelectivity(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesLowSelectivity()
        else:
            a = self.triples.allTriplesLowSelectivity()
        return a

    def instantiate(self, d):
        if isinstance(self.triples, list):
            ts = [t.instantiate(d) for t in self.triples]
            return JoinBlock(ts)
        else:
            return self.triples.instantiate(d)

    def instantiateFilter(self, d, filter_str):
        if isinstance(self.triples, list):
            ts = [t.instantiateFilter(d, filter_str) for t in self.triples]
            return JoinBlock(ts, filter_str)
        else:
            return self.triples.instantiateFilter(d, filter_str)

    def show2(self, w):
        n = SPARQL.nest(self.triples)
        if n:
            return SPARQL.aux2(n, w, " UNION ") + " ".join(map(str, self.filters))
        else:
            return " "

    def getVars(self):
        l = []
        for t in self.triples:
            l = l + t.getVars()
        return l

    def getConsts(self):
        c = []
        for t in self.triples:
            c = c + t.getConsts()
        return c

    def getPredVars(self):
        l = []
        for t in self.triples:
            l = l + t.getPredVars()
        return l

    def includeFilter(self, f):

        for t in self.triples:
            t.includeFilter(f)

    def places(self):
        p = 0
        for e in self.triples:
            p = p + e.places()
        return p

    def constantNumber(self):
        c = 0
        for e in self.triples:
            c = c + e.constantNumber()
        return c

    def const_subjects(self):
        c = 0
        for e in self.triples:
            c = c + e.const_subjects()
        return c

    def const_objects(self):
        c = 0
        for e in self.triples:
            c = c + e.const_objects()
        return c

    def const_predicates(self):
        c = 0
        for e in self.triples:
            c = c + e.const_predicates()
        return c

    def constantPercentage(self):
        return self.constantNumber()/self.places()


class JoinBlock(object):

    def __init__(self, triples, filters=None, filters_str=''):
        if filters is None:
            filters = []
        self.triples = triples
        self.filters = filters
        self.filters_str = filters_str

    def __repr__(self):
        r = ""
        if isinstance(self.triples, list):
            for t in self.triples:
                if isinstance(t, list):
                    r = r + " . ".join(map(str, t))
                elif t:
                    if r:
                        r = r + " . " + str(t)
                    else:
                        r = str(t)

            if len(self.filters) > 0:
                for f in self.filters:
                    r += str(f)

        else:
            r = str(self.triples)

            if len(self.filters) > 0:
                for f in self.filters:
                    r += str(f)

        return r #+ self.filters

    def setGeneral(self, ps, genPred):
        if isinstance(self.triples, list):
            for t in self.triples:
                t.setGeneral(ps, genPred)
        else:
            self.triples.setGeneral(ps, genPred)

    def allTriplesGeneral(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesGeneral()
        else:
            a = self.triples.allTriplesGeneral()
        return a

    def allTriplesLowSelectivity(self):
        a = True
        if isinstance(self.triples, list):
            for t in self.triples:
                a = a and t.allTriplesLowSelectivity()
        else:
            a = self.triples.allTriplesLowSelectivity()
        return a

    def show(self, x):
        if isinstance(self.triples, list):
            joinBody = ""
            for j in self.triples:
                if isinstance(j, list):
                    if joinBody:
                        joinBody = joinBody + ". ".join(map(str, j))
                    else:
                        joinBody = joinBody + " ".join(map(str, j))
                else:
                    if joinBody:
                        joinBody = joinBody + ". " + str(j)
                    else:
                        joinBody = joinBody + " " + str(j)
            if len(self.filters) > 0:
                for f in self.filters:
                    joinBody += str(f)
            return joinBody
            #return ". ".join(map(str, self.triples)) + " ".join(map(str, self.filters)) + self.filters_str
            #n = nest(self.triples)
            #if n:
            #    return aux(n, x, " . ") + " ".join(map(str, self.filters)) + self.filters_str
            #else:
            #    return " "
        else:
            return self.triples.show(x)

    def instantiate(self, d):
        if isinstance(self.triples, list):
            ts = [t.instantiate(d) for t in self.triples]
            return JoinBlock(ts, self.filters)
        else:
            return self.triples.instantiate(d)

    def instantiateFilter(self, d, filter_str):
        if isinstance(self.triples, list):
            ts = [t.instantiateFilter(d, filter_str) for t in self.triples]
            return JoinBlock(ts, self.filters, filter_str)
        else:
            return self.triples.instantiateFilter(d, filter_str)

    def show2(self, x):
        if isinstance(self.triples, list):
            n = SPARQL.nest(self.triples)
            if n:
                return SPARQL.aux2(n, x, " . ") + str(self.filters) + self.filters_str
            else:
                return " "
        else:
            return self.triples.show2(x)

    def getVars(self):
        l = []
        if isinstance(self.triples, list):
            for t in self.triples:
                l = l + t.getVars()
        else:
            l = self.triples.getVars()
        return l

    def getConsts(self):
        c = []
        if isinstance(self.triples, list):
            for t in self.triples:
                c = c + t.getConsts()
        else:
            c = self.triples.getConsts()

        return c

    def getPredVars(self):
        l = []
        if isinstance(self.triples, list):
            for t in self.triples:
                l = l + t.getPredVars()
        else:
            l = self.triples.getPredVars()
        return l

    def includeFilter(self, f):
        for t in self.triples:
            if isinstance(t, list):
                for s in t:
                    s.include_filter(f)
            else:
                t.includeFilter(f)

    def places(self):
        p = 0
        if isinstance(self.triples, list):
            for e in self.triples:
                p = p + e.places()
        else:
            p = self.triples.places()
        return p

    def const_subjects(self):
        c = 0
        if isinstance(self.triples, list):
            for e in self.triples:
                c = c + e.const_subjects()
        else:
            c = self.triples.const_subjects()
        return c

    def const_objects(self):
        c = 0
        if isinstance(self.triples, list):
            for e in self.triples:
                c = c + e.const_objects()
        else:
            c = self.triples.const_objects()
        return c

    def const_predicates(self):
        c = 0
        if isinstance(self.triples, list):
            for e in self.triples:
                c = c + e.const_predicates()
        else:
            c = self.triples.const_predicates()
        return c

    def constantNumber(self):
        c = 0
        if isinstance(self.triples, list):
            for e in self.triples:
                c = c + e.constantNumber()
        else:
            c = self.triples.constantNumber()
        return c

    def constantPercentage(self):
        return self.constantNumber()/self.places()


class Optional(object):

    def __init__(self, bgg):
        self.bgg = bgg

    def __repr__(self):
        return " OPTIONAL { " + str(self.bgg) + " }"

    def show(self, x):
        return x + "OPTIONAL {\n" + self.bgg.show(x + "  ") + "\n" + x + "}"

    def setGeneral(self, ps, genPred):
        self.bgg.setGeneral(ps, genPred)

    def getVars(self):
        return self.bgg.getVars()

    def getConsts(self):
        return self.bgg.getConsts()

    def getPredVars(self):
        return self.bgg.getPredVars()

    def places(self):
        return self.bgg.places()

    def allTriplesGeneral(self):
        return self.bgg.allTriplesGeneral()

    def allTriplesLowSelectivity(self):
        return self.bgg.allTriplesLowSelectivity()

    def instantiate(self, d):
        return Optional(self.bgg.instantiate(d))

    def instantiateFilter(self, d, filter_str):
        return Optional(self.bgg.instantiateFilter(d, filter_str))

    def constantNumber(self):
        return self.bgg.constantNumber()

    def const_subjects(self):
        return self.bgg.const_subjects()

    def const_objects(self):
        return self.bgg.const_obbjects()

    def const_predicates(self):
        return self.bgg.const_predicates()

    def constantPercentage(self):
        return self.constantNumber()/self.places()


class Triple(object):
    def __init__(self, subject, predicate, theobject):
        self.subject = subject
        self.predicate = predicate
        self.theobject = theobject
        self.isGeneral = False

    def __repr__(self):
        return "\n        " + self.subject.name + " " + self.predicate.name + " " + str(self.theobject)

    def setGeneral(self, ps, genPred):
        self.isGeneral = (SPARQL.getUri(self.predicate, ps) in genPred)

    def __eq__(self, other):

        return ((self.subject == other.subject) and
                (self.predicate == other.predicate) and
                (self.theobject == other.theobject))

    def __lt__(self, other):
        """
        compares two triples patterns based on the position of contants
        :param other:
        :return:
        """
        if other.subject.constant and not self.subject.constant:
            return False
        if self.subject.constant and not other.subject.constant:
            return True
        if other.predicate.constant and self.predicate.constant and other.theobject.constant and not self.theobject.constant:
            return False
        if other.predicate.constant and self.predicate.constant and self.theobject.constant and not other.theobject.constant:
            return True
        return self.constantPercentage() > other.constantPercentage()

    def const_subjects(self):
        n = 0
        if self.subject.constant:
            n = n + 1
        return n

    def const_objects(self):
        n = 0
        if self.theobject.constant:
            n = n + 1
        return n

    def const_predicates(self):
        n = 0
        if self.predicate.constant:
            n = n + 1
        return n

    def __hash__(self):
        return hash((self.subject, self.predicate, self.theobject))

    def allTriplesGeneral(self):
        return self.isGeneral

    #Modified 17-12-2013. General predicates are not considered to decide if the triple is selective or not
    def allTriplesLowSelectivity(self):
        return ((not self.predicate.constant)
                #or ((self.isGeneral) and (not self.subject.constant)
                 or ((not self.subject.constant)
                    and (not self.theobject.constant))
                 # or
                 #   # added 09/03/2018
                 #   (self.theobject.constant and
                 #   self.predicate.constant and
                 #   ('rdf:type' in self.predicate.name or 'a' == self.predicate.name or
                 #     'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in self.predicate.name))
                )

    def show(self, x):
        return x+self.subject.name+" " + self.predicate.name + " " + str(self.theobject)

    def getVars(self):

        l = []
        if not self.subject.constant:
            l.append(self.subject.name)
        if not self.theobject.constant:
            l.append(self.theobject.name)
        l.extend(self.getPredVars())
        return l

    def getConsts(self):
        c = []
        if self.subject.constant:
            c.append(self.subject.name)
        if self.theobject.constant:
            c.append(self.theobject.name)
        return c

    def getPredVars(self):

        l = []
        if not self.predicate.constant:
            l.append(self.predicate.name)
        return l

    def places(self):
        return 3

    def instantiate(self, d):
        sn = self.subject.name.lstrip('?$')
        pn = self.predicate.name.lstrip('?$')
        on = self.theobject.name.lstrip('?$')
        if (not self.subject.constant) and (sn in d):
            s = Argument(d[sn], True)
        else:
            s = self.subject
        if (not self.predicate.constant) and (pn in d):
            p = Argument(d[pn], True)
        else:
            p = self.predicate
        if (not self.theobject.constant) and (on in d):
            o = Argument(d[on], True)
        else:
            o = self.theobject
        return Triple(s, p, o)

    def instantiateFilter(self, d, filter_str):
        return Triple(self.subject, self.predicate, self.theobject)

    def constantNumber(self):
        n = 0
        if self.subject.constant:
            n = n + 1
        if self.predicate.constant:
            n = n + 1
        if self.theobject.constant:
            n = n + 1
        return n

    def constantPercentage(self):
        return self.constantNumber()/self.places()


class Filter(object):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        if (self.expr.op == 'REGEX' or self.expr.op == 'sameTERM' or self.expr.op == 'langMATCHES'):
            if (self.expr.op == 'REGEX' and self.expr.right.desc is not False):
                return "\n" + "FILTER " + self.expr.op + "(" + str(self.expr.left) + "," + self.expr.right.name + "," + self.expr.right.desc + ")"
            else:
                return "\n" + "FILTER " + self.expr.op + "(" + str(self.expr.left) + "," + str(self.expr.right) + ")"
        else:
            return "\n" + "FILTER (" + str(self.expr) + ")"

    def show(self, x):
        if self.expr.op == 'REGEX':
            if self.expr.right.desc is not False:
                return "\n" + "FILTER " + self.expr.op + "(" + str(self.expr.left) + "," + self.expr.right.name + "," + self.expr.right.desc + ")"
            else:
                return "\n" + x + "FILTER regex(" + str(self.expr.left) + "," + str(self.expr.right) + ")"
        else:
            return "\n" + x + "FILTER (" + str(self.expr) + ")"

    def getVars(self):
        return self.expr.getVars()

    def getConsts(self):
        return self.expr.getConsts()

    def getVarsName(self):
        vars=[]
        for v in self.expr.getVars():
            vars.append(v[1:len(v)])
        return vars

    def getPredVars(self):
        return []

    def setGeneral(self, ps, genPred):
        return

    def places(self):
        return self.expr.places()

    def allTriplesGeneral(self):
        return False

    def allTriplesLowSelectivity(self):
        return True

    def instantiate(self, d):
        return Filter(self.expr.instantiate(d))

    def instantiateFilter(self, d, filter_str):
        return Filter(self.expr.instantiateFilter(d, filter_str))

    def constantNumber(self):
        return 1
        #return self.expr.constantNumber()

    def constantPercentage(self):
        return 0.5
        #return self.constantNumber()/self.places()


class Expression(object):

    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        if self.op in SPARQL.unaryFunctor:
            return self.op + "(" + str(self.left) + ")"
        elif self.op in SPARQL.binaryFunctor:
            if self.op == 'REGEX' and self.right.desc is not False:
                return self.op + "(" + str(self.left) + "," + self.right.name + "," + self.right.desc + ")"
            else:
                return self.op + "(" + str(self.left) + "," + str(self.right) + ")"
        elif self.right is None:
            return self.op + str(self.left)
        else:
            return "(" + str(self.left) + " " + self.op + " " + str(self.right) + ")"

    def getVars(self):
        #if (self.op=='REGEX' or self.op == 'xsd:integer' or self.op=='!' or self.op == 'BOUND' or self.op == 'ISIRI' or self.op == 'ISURI' or self.op == 'ISBLANK' or self.op == 'ISLITERAL' or self.op == 'STR' or self.op == 'LANG' or self.op == 'DATATYPE'):
        if (self.op in SPARQL.unaryFunctor) or (self.op in SPARQL.binaryFunctor) or (self.right is None):
            return self.left.getVars()
        else:
            return self.left.getVars()+self.right.getVars()

    def getConsts(self):
        if self.op in SPARQL.unaryFunctor or self.right is None:
            return self.left.getConsts()
        elif self.op in SPARQL.binaryFunctor:
            return self.right.getConsts()
        else:
            return self.left.getConsts() + self.right.getConsts()

    def instantiate(self, d):
        return Expression(self.op, self.left.instantiate(d),
                          self.right.instantiate(d))

    def instantiateFilter(self, d, filter_str):
        return Expression(self.op, self.left.instantiateFilter(d, filter_str),
                          self.right.instantiateFilter(d, filter_str))

    def allTriplesGeneral(self):
        return False

    def allTriplesLowSelectivity(self):
        return True

    def setGeneral(self, ps, genPred):
        return

    def places(self):
        if (self.op in SPARQL.unaryFunctor)or (self.op == 'REGEX' and self.right.desc is False):
            return self.left.places()
        else:
            return self.left.places() + self.right.places()

    def constantNumber(self):
        if (self.op in SPARQL.unaryFunctor) or (self.op == 'REGEX' and self.left.desc is False):
            return self.left.constantNumber()
        else:
            return self.left.constantNumber() + self.right.constantNumber()

    def constantPercentage(self):
        return self.constantNumber()/self.places()


class Argument(object):

    def __init__(self, name, constant, desc=False, datatype=None, lang=None, isuri=False, dtype=None):
        self.name = name
        self.constant = constant
        # desc var is used to flag if Variable is used in ORDER BY DESC clause
        self.desc = desc
        self.datatype = datatype
        self.lang = lang
        self.isUri = isuri
        self.dtype = dtype

    def __repr__(self):
        arg = self.name
        if self.datatype is not None:
            arg += "^^" + self.datatype
        if self.lang is not None:
            arg += "@" + self.lang

        return arg

    def __str__(self):
        arg = self.name
        if self.datatype is not None:
            arg += "^^" + self.datatype
        elif self.lang is not None:
            arg += "@" + self.lang

        return arg

    def __eq__(self, other):
        return self.name == other.name and self.constant == other.constant

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self.name, self.constant))

    def getVars(self):
        if self.constant:
            return []
        else:
            return [self.name]

    def getConsts(self):

        if self.constant:
            n = self.name
            if self.datatype is not None:
                n = n + "^^" + self.datatype
            elif self.lang is not None:
                n = n + "@" + self.lang
            return [n]
        else:
            return []

    def places(self):
        return 1

    def constantNumber(self):
        n = 0
        if self.constant:
            n = n + 1
        return n

    def constantPercentage(self):
        return self.constantNumber()/self.places()

