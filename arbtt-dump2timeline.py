"""
This script parses adbtt-dump output and produces a plot of your activity.
The goal is to produce similar output as given by ManicTime standalone application.

By default reads "adbtt-dump -t JSON" output from stdin. It is a list of samples, 
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

INACTIVE_THRESHOLD = 5*60*1000 # 5 minutes

def get_local_tz():
    now = datetime.now()
    local_now = now.astimezone()
    local_tz = local_now.tzinfo
    return local_tz

def plot_arbtt_dump(data, roi_span_start = None, roi_span_end = None):

    local_tz = get_local_tz()
    prev_title = None
    prev_timestamp = None
    tasks = []

    for sample in data:
        timestamp = parser.parse(sample['date']).astimezone(local_tz)
        if roi_span_start and (timestamp<roi_span_start or timestamp>roi_span_end):
            continue

        
        active_title = next(( (w['program'], w['title'])
            for w in sample['windows'] if w['active']), None)
        is_incative = sample['inactive']>INACTIVE_THRESHOLD

        # TODO: this is wrong, the incative is not a continous span. Fix it.
        if is_incative:
            tasks.append( dict(Task="", Start=prev_timestamp, Finish=timestamp, Program="INACTIVE" ) )
            prev_timestamp = timestamp
            prev_title = None
            continue

        if active_title and active_title!=prev_title:
            if prev_title:
                tasks.append( dict(Task=" : ".join(active_title), Start=prev_timestamp, Finish=timestamp, Program=active_title[0]) )

            prev_timestamp = timestamp
            prev_title = active_title

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
    argparser = argparse.ArgumentParser(description='Produces a timeline plot for arbtt-dump JSON output.')
    argparser.add_argument("--today", help="only show activity of the current day", action="store_true")
    args = argparser.parse_args()
    roi_span_start, roi_span_end = None, None
    if args.today:
        roi_span_start = datetime.combine(date.today(), datetime.min.time()).astimezone()
        roi_span_end = roi_span_start+timedelta(hours=24)

    data = json.load(sys.stdin)
    plot_arbtt_dump(data, roi_span_start, roi_span_end)

