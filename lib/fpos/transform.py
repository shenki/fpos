#!/usr/bin/python3
#
#    Transforms a transaction document into budget IR
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
import sys
from datetime import datetime
import time
import calendar
from .core import money
from .core import date_fmt

months = [calendar.month_abbr[i] for i in range(1, 13)]

transform_choices = sorted([ "anz", "commbank", "stgeorge", "nab" ])
cmd_description = \
        """Not all bank CSV exports are equal. fpos defines an intermediate
        representation (IR) which each of the tools expect as input to eventually
        generate spending graphs. The job of the transform subcommand is to
        take each bank's CSV transaction schema and convert it to fpos' IR.
        Typically transform is the first command used in the fpos chain."""
cmd_help = \
        """Transform a transaction CSV document into fpos intermediate
        representation"""

def _take_three(src):
    def _gen():
        for l in src:
            yield [ l[0], money(float(l[1])), l[2] ]
    return _gen()

def transform_commbank(csv):
    # Commbank format:
    #
    # Date,Amount,Description,Balance
    return _take_three(csv)

def transform_anz(csv):
    # Identity transform, ANZ's format meets IR:
    #
    # Date,Amount,Description
    return _take_three(csv)

def transform_stgeorge(csv):
    # St George Bank, first row is header
    #
    # Date,Description,Debit,Credit,Balance
    #
    # Discard header
    next(csv)
    def _gen():
        for l in csv:
            date = l[0]
            amount = money((-1.0 * float(l[2])) if l[2] else float(l[3]))
            description = l[1]
            for chunk in description.split():
                if months.count(chunk[2:5]) != 1:
                    continue
                if len(chunk) == 5:
                    new_time = time.strptime(chunk, "%d%b")
                elif len(chunk) == 10:
                    new_time = time.strptime(chunk, "%d%b%H:%M")
                else:
                    continue
                # Handle dates around new years. Assume a correction of no
                # more than 1 month
                given_time = time.strptime(date, "%d/%m/%Y")
                if abs(given_time.tm_mon - new_time.tm_mon) > 1:
                    continue
                new_date = time.strftime("%d/%m", new_time)
                date = new_date + date[-5:]
                description = description.replace(chunk, "", 1)
            yield [date, amount, description]
    return _gen()

_nab_date_fmt = "%d-%b-%y"

def transform_nab(csv):
    # NAB format:
    #
    # Date, Amount, Ref #,, Description, Merchant, Remaining Balance
    # 28-Apr-14,-64.67,071644731756,,CREDIT CARD PURCHASE,BP CRAFERS 9125 CRAFERS,-169.28,
    def _gen():
        for l in csv:
            ir_date = datetime.strptime(l[0], _nab_date_fmt).strftime(date_fmt)
            ir_amount = money(float(l[1]))
            ir_description = " ".join(e for e in l[4:6] if (e is not None and "" != e ))
            yield [ ir_date, ir_amount, ir_description ]
    return _gen()

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    form_str = "The CSV schema used by the input file, named after " \
            "associated banks. Options are: %s" % ' '.join(transform_choices)
    parser.add_argument("form", metavar="FORM", choices=transform_choices,
            help=form_str)
    parser.add_argument("infile", metavar="INPUT", type=argparse.FileType('r'), default=sys.stdin,
            help="The source file whose contents should be transformed to fpos IR")
    parser.add_argument("outfile", metavar="OUTPUT", type=argparse.FileType('w'), default=sys.stdout,
            help="The destination file to which the IR will be written")
    return None if subparser else parser.parse_args()

def transform(form, source):
    assert form in transform_choices
    return globals()["transform_{}".format(form)](source)

def main(args=None):
    if args is None:
        args = parse_args()
    try:
        csv.writer(args.outfile).writerows(transform(args.form, csv.reader(args.infile)))
    finally:
        args.infile.close()
        args.outfile.close()

if __name__ == "__main__":
    main()
