#!/usr/bin/env python
"""
This script parses adbtt-dump output and produces a plot of your activity.
The goal is to produce similar output as given by ManicTime standalone application.

By default reads "arbtt-dump -t JSON" output from stdin. It is a list of samples, 
an example is given below:

{
    "desktop": "Workspace 1",
    "inactive": 65,
    "date": "2022-09-21T10:26:27.90676109Z",
    "windows": [
        {
            "active": true,
            "program": "gnome-terminal-server",
            "title": "jhr@pieni: ~"
        },
        {
            "active": false,
            "program": "org.gnome.Nautilus",
            "title": "Pictures"
        },
    ],
    "rate": 60000
}

So, for example:

arbtt-dump -t JSON | python3 arbtt-dump2timeline.py --today

In case your arbtt database grows too big, just split it. Or.

 arbtt-dump -t JSON | echo "[$(grep 2023-08-01T)" | python3 arbtt-dump2timeline.py --today

"""

from dateutil import parser
from datetime import date, datetime, timedelta
import plotly.express as px
import pandas as pd
import sys, json;
import copy

DEFAULT_INACTIVE_THRESHOLD = 5*60 # 5 minutes

def get_local_tz():
    now = datetime.now()
    local_now = now.astimezone()
    local_tz = local_now.tzinfo
    return local_tz

def convert_arbtt_dump(data, inact_th, roi_span_start = None, roi_span_end = None):
    local_tz = get_local_tz()
    prev_title = None
    prev_timestamp = None
    tasks = []

    for sample in data:
        timestamp = parser.parse(sample['date']).astimezone(local_tz)
        #print("compare", roi_span_start, "<", timestamp, "<", roi_span_end)
        if roi_span_start and (timestamp<roi_span_start or timestamp>roi_span_end):
            continue
        
        active_title = next(( (w['program'], w['title'])
            for w in sample['windows'] if w['active']), None)
        is_incative = sample['inactive']>inact_th*1000

        if is_incative:
            # remove until when inactivity started
            remove_until = timestamp-timedelta(milliseconds=int(sample['inactive']))
            org_tasks = copy.deepcopy(tasks)
            if len(tasks)>0:
                try:
                    while tasks[-1]["Start"] > remove_until:
                        tasks.pop()
                    # Fix the last non-inactive
                    if tasks[-1]["Program"]!="AFK" and tasks[-1]["Finish"]>remove_until:
                        tasks[-1]["Finish"] = remove_until
                except:
                    print("FIXME", org_tasks)

            tasks.append( dict(Task="", Start=remove_until, Finish=timestamp, Program="AFK" ) )
            prev_timestamp = timestamp
            prev_title = None
        else:
            if active_title:
                if active_title==prev_title:
                    prev_timestamp = tasks[-1]["Start"]
                    tasks.pop() # replace previous
                tasks.append( dict(Task=" : ".join(active_title), Start=prev_timestamp, Finish=timestamp, Program=active_title[0]) )
                prev_timestamp = timestamp
                prev_title = active_title

    if len(tasks)==0:
        return None

    df = pd.DataFrame(tasks)

    return df

def plot_arbtt_dump(data, inact_th, roi_span_start = None, roi_span_end = None):

    df = convert_arbtt_dump(data, inact_th, roi_span_start, roi_span_end)
    if df is None or df.empty:
        print("No data")
    return

    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Program", hover_name="Task", color="Program")
    fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
    fig.update_layout(
    legend = dict(
        x = 0,
        y = 1.2)
    )
    fig.show()

if __name__=="__main__":
    import argparse
    argparser = argparse.ArgumentParser(description='Produces a timeline plot from raw arbtt-dump JSON output.',
        epilog='Example of use:\n'+'arbtt-dump -t JSON | ./arbtt-dump2timeline.py --date 2022-12-02')
    dategroup = argparser.add_mutually_exclusive_group()
    dategroup.add_argument("--today", help="only show activity of the current day", action="store_true")
    dategroup.add_argument("--yesterday", help="only show activity of the previous day", action="store_true")
    dategroup.add_argument("--date", help="only show activity for a given date")
    argparser.add_argument("--inact", help="interpret this long inactivity as AFK (in seconds, default %d)"%DEFAULT_INACTIVE_THRESHOLD,
                           type=int, default=DEFAULT_INACTIVE_THRESHOLD)
    
    args = argparser.parse_args()
    roi_span_start, roi_span_end = None, None
    set_date = None
    if args.today:
        set_date = date.today()
    if args.yesterday:
        set_date = date.today()-timedelta(days=1)
    if args.date:
        set_date = parser.parse(args.date)
        print("Using date", set_date)
    
    if set_date is not None:
        if isinstance(set_date, date):
            roi_full_day_span_start = datetime.combine(set_date, datetime.min.time()).astimezone()
            roi_span_start = roi_full_day_span_start
        else:
            roi_span_start = datetime.combine(set_date.date(), set_date.time()).astimezone()
            roi_full_day_span_start = datetime.combine(roi_span_start.date(), datetime.min.time()).astimezone()

        roi_span_end = roi_full_day_span_start+timedelta(hours=24)
        print("Using date", roi_span_start)
        print("Using date", roi_span_end)

    data = json.load(sys.stdin)
    plot_arbtt_dump(data, args.inact, roi_span_start, roi_span_end)

