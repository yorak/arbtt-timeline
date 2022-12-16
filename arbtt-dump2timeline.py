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
"""

from dateutil import parser
from datetime import date, datetime, timedelta
import plotly.express as px
import pandas as pd
import sys, json;

DEFAULT_INACTIVE_THRESHOLD = 5*60 # 5 minutes

def get_local_tz():
    now = datetime.now()
    local_now = now.astimezone()
    local_tz = local_now.tzinfo
    return local_tz

def plot_arbtt_dump(data, inact_th, roi_span_start = None, roi_span_end = None):

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

        # TODO: this is wrong, the incative is not a continous span. Fix it.
        if is_incative:
            # remove until when inactivity started
            remove_until = timestamp-timedelta(milliseconds=int(sample['inactive']))
            if len(tasks)>0:
                while tasks[-1]["Start"] > remove_until:
                    tasks.pop()
                # Fix the last non-inactive
                if tasks[-1]["Program"]!="AFK" and tasks[-1]["Finish"]>remove_until:
                    tasks[-1]["Finish"] = remove_until

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
        return

    df = pd.DataFrame(tasks)

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
    argparser.add_argument("--today", help="only show activity of the current day", action="store_true")
    argparser.add_argument("--date", help="only show activity for a given date")
    argparser.add_argument("--inact", help="interpret this long inactivity as AFK (in seconds, default %d)"%DEFAULT_INACTIVE_THRESHOLD,
                           type=int, default=DEFAULT_INACTIVE_THRESHOLD)
    
    args = argparser.parse_args()
    roi_span_start, roi_span_end = None, None
    set_date = None
    if args.today:
        set_date = date.today()
    if args.date:
        set_date = parser.parse(args.date)
    
    if set_date is not None:
        roi_span_start = datetime.combine(set_date, datetime.min.time()).astimezone()
        roi_span_end = roi_span_start+timedelta(hours=24)

    data = json.load(sys.stdin)
    plot_arbtt_dump(data, args.inact, roi_span_start, roi_span_end)

