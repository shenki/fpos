#!/usr/bin/python3
#
#    Visualises an annotated budget IR document
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

import copy
import csv
import calendar
from datetime import datetime
import itertools
import math
from .core import categories, flexible, fixed
from .core import money
from .core import date_fmt, month_fmt

cmd_description = \
        """Displays a number of graphs from an annotated IR document. The graphs include:
        
        stacked_bar_expenses: Total expenditure each month,
        bar_margin: Real and projected surplus or loss,
        box_categories: Box-plot describing spending per month in each category,
        xy_categories: Per-category XY-plots of expenditure,
        xy_weekly: XY-plot of total weekly expenditure,
        bar_targets: A budget derived from mean expenditure per category"""
cmd_help = \
        """Display spending as graphs of various forms using the category
        annotations added to the IR by the annotate subcommand"""

blacklist = ("Income", "Internal")
whitelist = [x for x in categories if x not in blacklist]

extract_month = lambda x: datetime.strptime(x, date_fmt).strftime("%m/%Y")
extract_week = lambda x: datetime.strptime(x, date_fmt).strftime("%Y:%U")
datesort = lambda x : datetime.strptime(x, date_fmt).date()
monthsort = lambda x : datetime.strptime(x, month_fmt).date()
monthname = lambda x : datetime.strptime(x, month_fmt).strftime("%b")

def group_period(reader, extract=[extract_month]):
    l = [ {} for e in extract ]
    for row in reader:
        for i, e in enumerate(extract):
            d = e(row[0])
            if d not in l[i]:
                l[i][d] = []
            l[i][d].append(row)
    return l

def sum_categories(data):
    summed = dict((x, 0) for x in categories)
    for row in data:
        summed[row[3]] += float(row[1])
    return summed

def sum_expenses(expenses):
    summed = {}
    for m, cs in expenses.items():
        if m not in summed:
            summed[m] = 0
        for v in cs.values():
            summed[m] += v
    return summed

def income(summed):
    d = dict((m, 0) for m in summed.keys())
    d.update(dict((m, c["Income"]) for m, c in summed.items() if "Income" in c))
    return d

def invert(summed, valid):
    d = {}
    ms = []
    for m, v in summed.items():
        ms.append(m)
        for c, s in v.items():
            if c not in d:
                d[c] = {}
            if m not in d[c]:
                d[c][m] = 0
            d[c][m] += s
    for c in valid:
        if c not in d:
            d[c] = dict((m, 0) for m in ms)
    return d

def category_sum_matrix(summed):
    return [ [ summed[k][v] for v in sorted(summed[k], key=monthsort) ] for k in sorted(summed) ]

def ignore(summed, *args):
    d = copy.deepcopy(summed)
    for k in args:
        for m in d.keys():
            del d[m][k]
    return d

def surplus(expenses, income):
    s = {}
    for m, c in expenses.items():
        s[m] = income[m] + sum(c.values())
    return s

def colours(n):
    return plt.cm.BuPu(np.linspace(0, 1.0, n))

def name():
    return __name__.split(".")[-1]

def parse_args(subparser=None):
    import argparse
    parser_init = subparser.add_parser if subparser else argparse.ArgumentParser
    parser = parser_init(name(), description=cmd_description, help=cmd_help)
    graph_choices = [ "stacked_bar_expenses", "bar_margin", "box_categories",
            "xy_categories", "xy_weekly", "bar_targets" ]
    parser.add_argument("database", metavar="FILE", type=argparse.FileType('r'),
            help="The IR document of which to draw graphs")
    parser.add_argument("--save", type=float, default=0,
            help="Adjust the budget to try save the provided amount")
    parser.add_argument("--graph", choices=graph_choices,
            help="Display a single graph rather than all")
    parser.add_argument("--current-date", default=False, action="store_true",
            help="Draw graphs based on the current date rather than the date of the last transaction")
    return None if subparser else parser.parse_args()

def should_graph(name, graph):
    return None is name or name == graph

def bar_label(plot, rects, values, oriented="v", offset=130):
    for i, rect in enumerate(rects):
        if oriented == "v":
            x = rect.get_x() + rect.get_width()/2.
            y = values[i] + math.copysign(offset, values[i])
        else:
            x = values[i] + math.copysign(offset, values[i])
            y = rect.get_y() + rect.get_height()/3.
        text = '\${}'.format(int(values[i]))
        plot.text(x, y, text, ha='center', va='bottom')

def q1(boxprop):
    return boxprop.get_data()[1][2]

def q3(boxprop):
    return boxprop.get_data()[1][1]

def mean_error(data, level=0.95):
    n, min_max, mean, var, skew, kurt = stats.describe(data)
    dscale = math.sqrt(var) / math.sqrt(len(data))
    R = stats.norm.interval(level, loc=mean, scale=dscale)
    return R[1] - mean

def graph_stacked_bar_expenses(months, monthlies, expenses, m_income, remaining):
    # Looks like:
    # { "04/2013" : 3905.07, ... }
    m_margin = surplus(expenses, m_income)
    # Plot table/bar-graph of expenses
    n_months = len(months)
    y_offset = np.array([0.0] * n_months)
    bar_width = 0.4
    cell_text = []
    palette = colours(len(whitelist))
    # Add colours for metadata rows total, income and surplus
    plt.figure(1)
    for i, row in enumerate(monthlies):
        plt.bar(np.arange(n_months) + 0.3, row, bar_width, bottom=y_offset, color=palette[i])
        y_offset = y_offset + row
        cell_text.append([money(float(x)) for x in row])
    cell_text.append([money(sum(expenses[m].values())) for m in months])
    cell_text.append([money(m_income[k]) for k in months])
    cell_text.append([money(m_margin[k]) for k in months])
    plt.table(cellText=cell_text,
        rowLabels=whitelist + [ "Expenditure", "Income", "Surplus" ],
        # Add white for metadata
        rowColours=[x for x in itertools.chain(palette, [[1] * 4] * 3)],
        colLabels=months,
        loc="bottom")
    plt.ylabel("Dollars ($), spent < 0, earnt > 0")
    plt.subplots_adjust(left=0.15, bottom=0.3)
    plt.xticks([])
    plt.xlim([0, n_months])
    plt.grid(axis="y")
    plt.title("Expenditures by Category per Month\n{} Day(s) Remaining in {}".format(remaining, months[-1]))

def graph_bar_margin(months, m_income, expenses, remaining, save=0):
    if 1 == len(months):
        # Need more than one month's data
        print("Cannot display bar_margin, not enough data")
        return
    # Looks like:
    # { "04/2013" : 3905.07, ... }
    m_margin = surplus(expenses, m_income)
    # Plot bar graph of margin
    f = plt.figure(2)
    _graph_bar_margin_previous(plt.subplot(121), months[:-1], m_margin)
    _graph_bar_margin_current(plt.subplot(222), months, m_income, expenses, save)
    _graph_bar_margin_spending(plt.subplot(224), months, m_income, expenses, save, remaining)
    f.suptitle("Remaining Capital after Expenses\n{} Days Remaining".format(remaining))

def _graph_bar_margin_previous(plot, months, m_margin):
    n_months = len(months)
    sorted_margins = [m_margin[k] for k in months]
    mbar = plot.bar(np.arange(n_months), sorted_margins, 0.6, align="center")
    bar_label(plot, mbar, sorted_margins)
    plot.axhline(0, color="black")
    plot.set_title("Previous Margins")
    plot.set_xlabel("Months")
    plot.set_ylabel("Margin ($)")
    plot.set_xlim([-1, len(months)])
    plot.set_xticks(np.arange(n_months))
    plot.set_xticklabels(months, rotation=30)
    plot.grid(axis="y")

def _graph_bar_margin_current(plot, months, m_income, expenses, save):
    c_month = months[-1]
    c_expenses = sum(expenses[c_month].values())
    c_income = m_income[c_month]
    margin = c_income + c_expenses
    mean_income = np.mean(list(m_income[m] for m in months[:-1]))
    title = "Earnings and Margins"
    ylabels = [ "Income", "Margin" ]
    earnt = [ c_income, margin ]
    projected = [ mean_income, mean_income + c_expenses ]
    if 0 < save:
        title += " and Targets"
        earnt.append(c_income + c_expenses - save)
        projected.append(mean_income + c_expenses - save)
        ylabels.append("Target")
    b_height = 0.4
    be = plot.barh(np.arange(len(earnt)) + 0.1, earnt, b_height, color="b")
    bar_label(plot, be, earnt, oriented="h", offset=500)
    bm = plot.barh(np.arange(len(projected)) + b_height + 0.1, projected, b_height, color="g")
    bar_label(plot, bm, projected, oriented="h", offset=500)
    plot.axvline(0, color="black")
    lims = [ 0, len(earnt)]
    plot.set_ylim(lims)
    plot.set_title(title)
    plot.set_yticks(np.arange(len(earnt)) + 0.5)
    plot.set_yticklabels(ylabels, rotation=15)
    plot.grid(axis="x")
    plot.legend((be, bm), ("Earnt", "Projected"))

def _graph_bar_margin_spending(plot, months, m_income, expenses, save, remaining):
    mean_income = np.mean(list(m_income[m] for m in months[:-1]))
    c_month = months[-1]
    c_expenses = sum(expenses[c_month].values())
    c_income = m_income[c_month]
    c_margin = c_income + c_expenses
    p_margin = mean_income + c_expenses
    e_per_day = max(0, (c_margin - save) / remaining)
    p_per_day = max(0, (p_margin - save) / remaining)
    e_per_week = max(0, e_per_day * 7)
    p_per_week = p_per_day * 7
    yes = [ e_per_day, e_per_week ]
    yps = [ p_per_day, p_per_week ]
    b1 = plot.barh(np.arange(len(yes)) + 0.1, yes, 0.4, color="b")
    bar_label(plot, b1, yes, oriented="h", offset=100)
    b2 = plot.barh(np.arange(len(yps)) + 0.5, yps, 0.4, color="g")
    bar_label(plot, b2, yps, oriented="h", offset=100)
    plot.axvline(0, color="black")
    mlen = max(len(x) for x in (yes, yps))
    lims = [ 0, mlen ]
    plot.set_ylim(lims)
    plot.set_yticks(np.arange(mlen))
    plot.set_yticklabels(( "Per Day", "Per Week" ), rotation=15)
    plot.set_yticks(np.arange(mlen) + 0.5)
    plot.grid(axis="x")
    plot.set_title("Spending Targets for Earnt and Projected Income")
    plot.legend(( b1, b2 ), ( "Earnt", "Projected"), loc="lower right")

def graph_box_categories(months, categorized):
    if 1 == len(months):
        # Need more than one month's data
        print("Cannot display box_categories, not enough data")
        return
    # Plot box-and-whisker plot of categories
    plt.figure(3)
    cs = []
    for c in whitelist:
        # Excludes the in-progress month
        cs.append([categorized[c][m] for m in months[:-1]])
    bpvs = plt.boxplot(cs)
    plt.table(cellText=[
        [money(x.get_data()[1][0]) for x in bpvs["medians"]],
        [money(q1(x)) for x in bpvs["boxes"]],
        [money(q3(x)) for x in bpvs["boxes"]],
        [money(max(c)) for c in cs],
        [money(min(c)) for c in cs]],
            rowLabels=["Median", "First Quartile", "Third Quartile", "Minimum", "Maximum"],
            colLabels=[x[:3] for x in whitelist],
            loc="bottom")
    plt.subplots_adjust(left=0.15, bottom=0.2)
    plt.xticks([])
    plt.ylabel("Dollars ($)")
    plt.grid(axis="y")
    plt.title("Box-plot of Expenses per Month\nSamples per category: {}".format(len(months) - 1))

def graph_xy_categories(months, categorized, remaining):
    if 1 == len(months):
        # Need more than one month's data
        print("Cannot display xy_categories, not enough data")
        return
    # XY plot of expenditure per category
    f, plts = plt.subplots(2, int(len(categorized) / 2), sharex=True)
    f.suptitle("XY Plot of Monthly Expenditure per Category")
    complete = months[:-1]
    monthr = np.arange(len(complete))
    monthns = [ monthname(x) for x in complete ]
    for p, k in zip(itertools.chain(*plts), whitelist):
        v = [ categorized[k][m] for m in complete ]
        # Values
        p.plot(monthr, v, 'o-')
        # Linear regression
        a, b = polyfit(monthr, v, 1)
        l = polyval([a, b], monthr)
        p.plot(monthr, l, 'r.-')
        p.set_title(k)
        p.set_xticks(range(len(monthns)))
        p.set_xticklabels(monthns, rotation=33)
        p.grid(axis="y")

def graph_xy_weekly(weekly):
    # Weekly XY plot with regression
    w_summed = [(i, sum(float(r[1]) for r in weekly[w] if r[3] in whitelist))
            for i,w in enumerate(sorted(weekly.keys()))]
    w_xys = list(zip(*w_summed))
    plt.figure(5)
    plt.plot(w_xys[0], w_xys[1], "bo-")
    a, b = polyfit(w_xys[0], w_xys[1], 1)
    l = polyval([a, b], w_xys[0])
    plt.plot(w_xys[0], l, "r.-")
    plt.title("XY Plot of Weekly Expenditure")
    plt.xlabel("Record Week (Arbitrary)")
    plt.ylabel("Expenditure ($)")
    plt.grid(axis="both")

def graph_bar_targets(months, monthlies, expenses, m_income, remaining, want_save):
    if 1 == len(months):
        # Need more than one month's data
        print("Cannot display bar_targets, not enough data")
        return
    # Target bar-graph - Current spending per category against mean
    plt.figure(6)
    # Remove the current month from monthlies
    prev_monthlies = [ e[:-1] for e in monthlies ]
    # Calculate the means for each category of each complete month
    mean_prev_monthlies = np.mean(prev_monthlies, axis=1)
    error_prev_monthlies = [ mean_error(e) for e in prev_monthlies ]
    curr_expenses = expenses[months[-1]]

    ms = dict(zip(whitelist, mean_prev_monthlies))
    # Calculate mean monthly income
    mean_income = np.mean([m_income[m] for m in months[:-1]])
    cash = mean_income
    # Subtract fixed costs
    cash -= abs(sum(v for k, v in ms.items() if k in fixed))
    # Subtract saving
    can_save = min(cash, want_save)
    cash -= can_save
    # Calculate flexible average sum
    fas = sum(ms[k] for k in flexible)
    # Estimate budget: Multiple remaining by flexible ratios
    fs = copy.deepcopy(ms)
    fs.update(dict((k, abs(ms[k] / fas) * cash) for k in flexible))
    budget = [ abs(fs[k]) for k in whitelist ]
    r_whitelist = np.arange(len(whitelist))
    b1 = plt.bar(r_whitelist + 0.1,
            budget,
            [ 0.6 ] * len(r_whitelist),
            alpha=0.4)
    b2 = plt.bar(r_whitelist + 0.1,
            [ abs(curr_expenses[k]) for k in whitelist ],
            [ 0.6 ] * len(r_whitelist),
            color='r', alpha=0.6)
    b3 = plt.bar(r_whitelist + 0.8,
            [ abs(v) for v in mean_prev_monthlies ],
            [ 0.1 ] * len(r_whitelist),
            yerr=error_prev_monthlies, color='k', alpha=0.6)
    plt.axhline(0, color="black")
    plt.xticks([])
    plt.ylabel("Position Against Budget / Mean Expense ($)")
    save_text = ( "\nSaving \${}"
            .format(money(can_save), money(mean_income)) )
    title = "Position for {} with {} days remaining{}\nBased on estimated income of ${}"\
            .format(months[-1], remaining, "" if 0 == want_save else save_text, money(mean_income))
    plt.title(title)
    expense_list = [ curr_expenses[c] for c in whitelist ]
    cell_text = []
    cell_text.append([money(abs(b) - abs(x)) for b, x in zip(budget, expense_list)])
    cell_text.append([money(abs(e)) for e in expense_list])
    cell_text.append([money(abs(b)) for b in budget])
    cell_text.append([money(abs(v)) for v in mean_prev_monthlies])
    cell_text.append([money(abs(v)) for v in error_prev_monthlies])
    plt.table(cellText=cell_text,
            rowLabels=[ "Position", "Spent", "Budget", "Mean", "+/- 95% Confidence" ],
            colLabels=[x[:3] for x in whitelist],
            loc="bottom")
    plt.subplots_adjust(left=0.15, bottom=0.2)
    plt.legend(( b1, b2, b3 ), ( "Budget", "Spent", "Mean Expenditure" ))
    plt.grid(axis="y")

def days_remaining(today):
    n_days = calendar.monthrange(today.year, today.month)[1]
    return (datetime(today.year, today.month, n_days) - today).days + 1

def main(args=None):
    from .core import global_module, global_symbol
    global_symbol(globals(), "scipy", "polyfit")
    global_symbol(globals(), "scipy", "polyval")
    global_module(globals(), "scipy.stats", name="stats")
    global_module(globals(), "matplotlib.pyplot", name="plt")
    global_module(globals(), "numpy", name="np")
    if args is None:
        args = parse_args()

    # Core data, used across multiple plots

    m_grouped, w_grouped = group_period(csv.reader(args.database),
            extract=[extract_month, extract_week])

    # m_summed: Looks like:
    #
    #  { "04/2013" : { "Cash" : -882.50, ... }, ... }
    m_summed = dict((m, sum_categories(v)) for m, v in m_grouped.items())

    # expenses: Looks like m_summed, but without blacklisted keys
    expenses = ignore(m_summed, *blacklist)

    # months: A list, containing the sorted set of months from expenses
    months = sorted(expenses, key=monthsort)

    # categorized: Looks like:
    #
    #  { "Cash" : { "04/2013" : -882.50, ... }, ... }
    categorized = invert(expenses, whitelist)

    # monthlies: Looks like:
    #
    # [
    #   [ -882.50, ... ], # Cash expenses per month
    #   [ -832.82, ... ], # Commitment expenses per month
    #   ...
    # ]
    monthlies = category_sum_matrix(categorized)

    # m_income: Looks like summed, but contains only income
    m_income = income(m_summed)


    # Grab the date of the most recent transaction in the database
    last_transaction = datetime.strptime(m_grouped[months[-1]][-1][0], date_fmt)
    if args.current_date:
        last_transaction = datetime.today()
    remaining = days_remaining(last_transaction)

    if (should_graph(args.graph, "stacked_bar_expenses")):
        graph_stacked_bar_expenses(months, monthlies, expenses, m_income, remaining)
    if (should_graph(args.graph, "bar_margin")):
        graph_bar_margin(months, m_income, expenses, remaining, args.save)
    if (should_graph(args.graph, "box_categories")):
        graph_box_categories(months, categorized)
    if (should_graph(args.graph, "xy_categories")):
        graph_xy_categories(months, categorized, remaining)
    if (should_graph(args.graph, "xy_weekly")):
        graph_xy_weekly(w_grouped)
    if (should_graph(args.graph, "bar_targets")):
        graph_bar_targets(months, monthlies, expenses, m_income, remaining, args.save)
    plt.show()

if __name__ == "__main__":
    main()
