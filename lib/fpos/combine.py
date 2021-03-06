#!/usr/bin/python3
#
#    Combines multiple budget IR documents into one
#    Copyright (C) 2013  Andrew Jeffery <andrew@aj.id.au>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import csv
import datetime
import hashlib
import itertools
import sys
from .core import date_fmt

cmd_description = \
        """Merges multiple IR documents into one time-ordered IR document. This
        is useful in a couple of scenarios, such as visualising spending across
        multiple accounts, or updating an existing transaction database with
        new transactions. In the latter case, the first file provided as an
        argument is treaded as the transaction database and all further files
        are treated as updates. The transaction database is expected (but is
        not required) to be an IR document which has all contained transactions
        annotated with spending categories; these categories take precedence
        over any annotated transactions in the update IR documents"""
cmd_help = \
        """Combines multiple IR documents into one time-ordered IR document"""

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    parser.add_argument("database", metavar="DATABASE", type=argparse.FileType('r'),
            help="An IR document which may or may not contain annotated transactions")
    parser.add_argument("updates", metavar="FILE", type=argparse.FileType('r'), nargs='*',
            help="An IR document to merge with DATABASE")
    parser.add_argument('--out', metavar="FILE", type=argparse.FileType('w'),
            default=sys.stdout, help="The destination for the merged document. Defaults to stdout")
    return None if subparser else parser.parse_args()

def digest_entry(entry):
    s = hashlib.sha1()
    for element in entry[:3]:
        s.update(str(element).encode("UTF-8"))
    return s.hexdigest()

def combine(sources):
    def _gen():
        entries = dict((digest_entry(x), x)
                for db in sources for x in db if 3 <= len(x))
        datesort = lambda x: datetime.datetime.strptime(x[0], date_fmt).date()
        costsort = lambda x: float(x[1])
        descsort = lambda x: x[2]
        for v in sorted(sorted(sorted(entries.values(), key=descsort), key=costsort), key=datesort):
            yield v
    return _gen()

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        readables = itertools.chain(args.updates, (args.database,))
        csv.writer(args.out).writerows(combine(csv.reader(x) for x in readables))
    finally:
        args.database.close()
        for e in args.updates:
            e.close()
        args.out.close()

if __name__ == "__main__":
    main()
