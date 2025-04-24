from PIL import Image, ImageDraw, ImageFont
import requests, json, textwrap, os, time, sys
import yaml
import pytz
import datetime
from ics import Calendar

def log( message ):
  logfile = 'clock.log'
  s = datetime.datetime.now().strftime('%H:%M:%S: ')
  
  print( message )
  return # We don't need to write to file currently
  with open( logfile, 'a' ) as f:
    f.write(s + message + '\n')

log('clock.sh start')
landscape = len( sys.argv ) > 1

# Set up image parameters
if landscape: WIDTH, HEIGHT = 800, 600
else: WIDTH, HEIGHT = 600, 800

BG_COLOR = (255, 255, 255)

# Set up font parameters
FONT_SIZE = 150
FONT_COLOR = 0 
FONT_PATH = "Roboto-Regular.ttf"

EVENTS_FILE = 'calendar.ics'
WEATHER_FILE = 'weather.json'
margin = 20
BBC_WEATHER_LOCATION_ID = 2643743

calendarurlfile = 'calendarurl.txt'
if os.path.isfile( calendarurlfile ):
  CALENDAR_URL = open( calendarurlfile, 'r' ).read().strip()
else:
  CALENDAR_URL = None

if CALENDAR_URL:
  events_age = ( time.time() - os.path.getmtime( EVENTS_FILE ) ) / 60
  if not os.path.isfile( EVENTS_FILE ) or events_age > 60:
    log('Fetching events')
    try:
      events = requests.get(CALENDAR_URL).text
      if len( events.strip() ) > 0:
        with open( EVENTS_FILE, 'w' ) as f:
          f.write(events)
    except Exception as e:
      log('FAIL: '+str(e))

locationidfile = 'weatherlocation.txt'
if os.path.isfile( locationidfile ):
  BBC_WEATHER_LOCATION_ID = int(open( locationidfile, 'r' ).read())

# Load font and create ImageDraw object
image = Image.new("L", (WIDTH, HEIGHT), color="white")
draw = ImageDraw.Draw(image)

# Draw time
time_str = datetime.datetime.now().strftime("%H:%M")
if landscape: 
  font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/1.5))
  time_width, time_height = draw.textsize(time_str, font=font)
  draw.text(( margin, 0), time_str, font=font, fill=FONT_COLOR)
else: 
  font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
  time_width, time_height = draw.textsize(time_str, font=font)
  draw.text(((WIDTH - time_width) / 2, 0), time_str, font=font, fill=FONT_COLOR)
time_width, time_height = draw.textsize(time_str, font=font)

# Draw date
date_str = datetime.datetime.now().strftime("%A %-d %B %Y")
if landscape: 
  font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE / 8 ) )
  date_width, date_height = draw.textsize(date_str, font=font)
  draw.text(( margin + (time_width/2) - (date_width/2), time_height + 10 ), date_str, font=font, fill=FONT_COLOR)
else: 
  font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE / 5 ) )
  date_width, date_height = draw.textsize(date_str, font=font)
  draw.text(((WIDTH - date_width) / 2, time_height + 10 ), date_str, font=font, fill=FONT_COLOR)

if landscape: line_y = time_height + date_height
else: line_y = time_height + date_height + 20

# Get weather data
if landscape: max_weather = 12
else: max_weather = 8

weather_age = ( time.time() - os.path.getmtime( WEATHER_FILE ) ) / 60
if not os.path.isfile( WEATHER_FILE ) or weather_age > 60:
  log('Fetching weather data')
  
  try:
    # Cache the weather
    url = 'https://weather-broker-cdn.api.bbci.co.uk/en/forecast/aggregated/' + str(BBC_WEATHER_LOCATION_ID)
    weather = requests.get(url).json()
    with open( WEATHER_FILE, 'w' ) as f:
      f.write(json.dumps(weather))
  except Exception as e:
    log('FAIL: '+str(e))
  log('Done fetching weather data')
else:
  try:
    with open( WEATHER_FILE, 'r' ) as f:
      weather = json.loads( f.read() )

    # Just get the next 8 hours
    reports = []
    if weather and 'forecasts' in weather:
      for report in weather['forecasts'][0]['detailed']['reports']:
        if len( reports ) >= max_weather: break
        reports.append( report )

    # Draw weather
    i=1
    if landscape: spacing = int( (HEIGHT-line_y)/(len(reports)+1) )
    else: spacing = int( WIDTH/(len(reports)+1) )
    font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE / 12 ) )
    ICON_SIZE = 40
    for r in reports:
      if landscape:
        x = margin + int(ICON_SIZE/2)
        y = i * spacing + line_y
      else:
        x = (i*spacing) 
        y = line_y

      # Weather icon
      icon = Image.open('icons/' + str( r['weatherType'] ) + '.png').convert('L').resize((ICON_SIZE,ICON_SIZE))
      image.paste(icon,(x-int(ICON_SIZE/2),y))
      if landscape: x+=ICON_SIZE

      # Time slot
      width, height = draw.textsize( r['timeslot'], font=font)
      if landscape:
        draw.text((x,y), r['timeslot'], font=font, fill=FONT_COLOR)
      else:
        draw.text((x-int(width/2),line_y+ICON_SIZE+height), r['timeslot'], font=font, fill=FONT_COLOR)
      
      # Temperature and precipitation
      temp_and_precip = str( r['temperatureC'] ) + '° ' + str( r['precipitationProbabilityInPercent'] ) + '%'
      width, height = draw.textsize( temp_and_precip, font=font)
      if landscape: 
        x+=50
        draw.text((x,y), temp_and_precip, font=font, fill=FONT_COLOR)
      else:
        draw.text((x-int(width/2),y+ICON_SIZE), temp_and_precip, font=font, fill=FONT_COLOR)
      i+=1
      # print( report )
      # print(report['timeslot'],report['weatherType'],report['temperatureC'],report['precipitationProbabilityInPercent'])

    if not landscape: 
      line_y += 90
      line_x = margin

  except Exception as e:
    log('FAIL: ' + str(e))

if landscape: 
  line_y = 0
  line_x = int(WIDTH/2.5)
else:
  line_x = margin

# Load event data from vCalendar file
events = []
running = []
imminent = []
comingup = []
try:
  with open(EVENTS_FILE, "r") as f:
    c = Calendar(f.read())
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    timezone = datetime.datetime.now(datetime.timezone(datetime.timedelta(0))).astimezone().tzinfo
    for event in c.events:
      if event.end < now: continue
      if '(0.25)' in event.name: continue
      event_data = {
        "date": event.begin.astimezone(timezone).strftime("%Y-%m-%d"),
        "date_str": event.begin.astimezone(timezone).strftime("%A %-d %B"),
        "day": event.begin.astimezone(timezone).strftime("%A"),
        "start": event.begin.astimezone(timezone).strftime("%H:%M"),
        "end": event.end.astimezone(timezone).strftime("%H:%M"),
        "name": event.name,
        "start_timestamp": event.begin.timestamp(),
        "end_timestamp": event.end.timestamp(),
        "duration": int( ( event.end.astimezone(timezone) - event.begin.astimezone(timezone) ).seconds / 60 )
      }

      # If it's longer than 2 hours it's probably some kind of all day event
      if event_data['duration'] > 120 or event_data['duration'] == 0: continue
     
      events.append(event_data)
      
      # Currently running event?
      if event.end.timestamp() > datetime.datetime.timestamp( now ) and event.begin.timestamp() <= datetime.datetime.timestamp( now ):
        running.append(event_data)
        continue

      # Starting imminently
      if ( ( event.begin.timestamp() - datetime.datetime.timestamp( now ) ) / 60 ) < 6:
        imminent.append( event_data )
        continue

      # Coming up
      if ( ( event.begin.timestamp() - datetime.datetime.timestamp( now ) ) / 60 ) < 60:
        comingup.append( event_data )

  # Order by date
  events = sorted(events, key=lambda x: x['date'] + x['start'])
except Exception as e:
  log('FAIL reading from events: ' + str(e))


# print(json.dumps(events,indent=2))

def draw_block( title, titlesize, items ):
  global line_x, line_y, margin, landscape
  if len( items ) == 0: return
  items = sorted(items, key=lambda x: x['date'] + x['start'])

  if landscape: titlesize = int(titlesize * 0.9)

  # Title
  font = ImageFont.truetype(FONT_PATH, titlesize)  
  title_width, title_height = draw.textsize( title, font=font)
  draw.text((line_x, line_y), title, font=font, fill=FONT_COLOR)
  line_y += title_height

  # Number of mins til start
  font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE/6 ))
  starting = int( ( items[0]['start_timestamp'] - time.time() ) / 60 )
  subtitle = ''
  if starting > 0:
    subtitle = 'in ' + str( starting ) + ' mins'
  else:
    subtitle = str(-1*starting) + ' mins ago'
  subtitle_width, subtitle_height = draw.textsize( title, font=font)
  draw.text((line_x, line_y), subtitle, font=font, fill=FONT_COLOR)
  line_y += subtitle_height
    
  # List events
  txt = []
  for event in items:
    txt.append( '\n'.join( textwrap.wrap( event["name"], width=30 ) ) )
  txt = '\n'.join(txt)
  font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/6))  
  width, height = draw.textsize( txt, font=font)
  if landscape: 
    draw.text((line_x, line_y), txt, font=font, fill=FONT_COLOR)
    line_y += height
  else: 
    draw.text((line_x+title_width, margin+line_y-title_height-subtitle_height), txt, font=font, fill=FONT_COLOR)
  line_y+=30
  
draw_block( 'NOW:', int( FONT_SIZE/2 ), running )
draw_block( 'Imminent:', int( FONT_SIZE/4 ), imminent )
draw_block( 'Coming up:', int( FONT_SIZE/6 ), comingup )

# Draw events 
line_y += 10
date_font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/8))
start_font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/3))
end_font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/8))
event_font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/8))
day = None
if landscape: wrapwidth=40
else: wrapwidth=50

for event in events:

    if day != event['date']:
      date_width, date_height = draw.textsize( event['date_str'], font=date_font)
      draw.text( ( line_x, line_y), event['date_str'], font=date_font)
      line_y += date_height
      day = event['date']

    start_text = f'{event["start"]}'
    end_text = f'{event["end"]} ({event["duration"]})'
    event_text = '\n'.join( textwrap.wrap( event["name"], width=wrapwidth ) )
    start_width, start_height = draw.textsize( start_text, font=start_font)
    end_width, end_height = draw.textsize( end_text, font=end_font)
    event_width, event_height = draw.textsize( event_text, font=event_font)
    if line_y + event_height > HEIGHT:
        break
    draw.text((line_x, line_y), start_text, font=start_font, fill=FONT_COLOR)
    draw.text((line_x, line_y+start_height), end_text, font=end_font, fill=FONT_COLOR)
    draw.text((line_x+start_width+10, line_y + 10), event_text, font=event_font, fill=FONT_COLOR)
    line_y += start_height + end_height + 20

# Save image to file
log('Save clock.png')

# Output the image if eips is a thing on this platform
import subprocess
if subprocess.run(['which','eips'], capture_output=True).stdout.decode().strip() == '/usr/sbin/eips':
  log('eips present')
 
  if landscape:
    log('Rotate image')
    image = image.transpose(Image.ROTATE_270)
  image.save("clock.png")
  cmd = ['eips']
  if time_str.endswith('00'): 
    log('Full draw')
    
    # Complete refresh once an hour
    cmd.append('-f')
  
  # Display the image
  log('Display clock.png')
  cmd.extend(['-g','clock.png'])
  subprocess.run(cmd)
else:
  image.save("clock.png")
log('Done')
