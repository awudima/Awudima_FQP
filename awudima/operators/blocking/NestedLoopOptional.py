'''
Created on Jul 10, 2011

Implements a Nested Loop Optional operator.
The intermediate results are represented as lists.

@author: Maribel Acosta Deibe
'''
from time import time
from multiprocessing import Queue
from awudima.operators.Optional import Optional
from awudima.operators.blocking.OperatorStructures import Table, Record


class NestedLoopOptional(Optional):

    def __init__(self, vars_left, vars_right):
        self.left_table  = Table()
        self.right_table = Table()
        self.results     = []
        self.vars_left   = set(vars_left)
        self.vars_right  = set(vars_right)
        self.vars        = list(self.vars_left & self.vars_right)

    def instantiate(self, d):
        newvars_left = self.vars_left - set(d.keys())
        newvars_right = self.vars_right - set(d.keys())
        return NestedLoopOptional(newvars_left, newvars_right)

    def execute(self, qleft, qright, out):
        # Executes the Nested Loop Optional.
        self.left = []
        self.right = qright
        self.qresults = out

        # Initialize tuple.
        tuple = None

        # GEt tuple from queue.
        while not(tuple == "EOF"):
            tuple = qleft.get(True)
            self.left.append(tuple)

        # Get the variables to join.
        if (len(self.left)>1):
            # Iterate over the lists to get the tuples.
            while (len(self.left)>1):
                tuple = self.left.pop(0)
                self.insertAndProbe(tuple)

        # Put all the results in the output queue.
        while self.results:
            self.qresults.put(self.results.pop(0))

        # Put EOF in queue and exit.
        self.qresults.put("EOF")

    def insertAndProbe(self, tuple):
        # Executes the Nested Loop Join.

        # Get the attribute(s) to apply hash.
        att1 = ''
        for var in self.vars:
            att1 = att1 + tuple[var]
        i = hash(att1) % self.left_table.size;

        # Create record (tuple, ats, dts).
        record = Record(tuple, time(), 0)

        # Insert record in its corresponding partition.
        self.left_table.insertRecord(i, record)

        # Probe the record against its partition in the other table.
        self.probe(record, i, self.right_table.partitions[i], self.vars, self.right)


    def probe(self, record, i, partition, var, right):
        # Probe a tuple if the partition is not empty.
        if partition:
            anyjoin = False

            # For every record in the partition, check if it is duplicated.
            # Then, check if the tuple matches for every join variable.
            # If there is a join, concatenate the tuples and produce result.
            # If the partition was empty, or any join was produced, then contact the source.
            # If no match in the contacted source were produced, then concatenate with empty tuple.
            for r in partition.records:

                if self.isDuplicated(record, r):
                    break

                for v in var:
                    join = True
                    if record.tuple[v] != r.tuple[v]:
                        join = False
                        break

                if join:
                    anyjoin = True
                    res = record.tuple.copy()
                    res.update(r.tuple)
                    self.results.append(res)

            # Empty partition or no matches were found.
            if ((len(partition.records) == 0) or not(anyjoin)):
                instances = []
                for v in var:
                    instances = instances + [record.tuple[v]]

                # Contact the source.
                qright = Queue()
                right.execute(self.vars, instances, qright)


                # This is the join.
                # Insert in right table, and produce the results.
                # Get the tuples from right queue.
                rtuple = qright.get(True)
                if (not(rtuple == "EOF")):
                    while (not(rtuple == "EOF")):
                        res2 = rtuple.copy()

                        for v in var:
                            res2.update({v:record.tuple[v]})

                        reg = Record(res2, time(), 0)
                        self.right_table.insertRecord(i, reg)

                        res = rtuple.copy()
                        res.update(record.tuple)
                        self.results.append(res)

                        rtuple = qright.get(True)

                # This is the optional.
                # Construct empty tuple, insert in table, and produce the results.
                else:
                    res = {}

                    for k in self.right.atts:
                        res.update({k:''})

                    reg = Record(res, time(), 0)
                    self.right_table.insertRecord(i, reg)

                    res.update(record.tuple)
                    self.results.append(res)



    def isDuplicated(self, record1, record2):
        # Verify if the tuples has been already probed.
        return not record1.ats >= record2.ats
