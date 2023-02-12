# arbtt-timeline
Displays the arbtt-dump JSON output as a gantt chart / timeline similar to the one of ManicTime using Python and Plotly.

Usage:
``` 
arbtt-dump -t JSON | python3 arbtt-dump2timeline.py --today
```

If you have already made a backup with a different name, remember to give the file.

Usage:
```
arbtt-dump -f ~/.arbtt/capture.log.bu.2022-08-05_to_2023-02-12 -t JSON | python3 arbtt-dump2timeline.py --today
```
