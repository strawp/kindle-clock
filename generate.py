from PIL import Image, ImageDraw, ImageFont
import requests, json, textwrap, os, time
import yaml
import pyowm
import pytz
import datetime
from ics import Calendar

# Set up image parameters
WIDTH, HEIGHT = 600, 800
BG_COLOR = (255, 255, 255)

# Set up font parameters
FONT_SIZE = 150
FONT_COLOR = 0 
FONT_PATH = "Roboto-Regular.ttf"

EVENTS_FILE = 'calendar.ics'
WEATHER_FILE = 'weather.json'
margin = 20
BBC_WEATHER_LOCATION_ID = 2643743

locationidfile = 'weatherlocation.txt'
if os.path.isfile( locationidfile ):
  BBC_WEATHER_LOCATION_ID = int(open( locationidfile, 'r' ).read())

# Load font and create ImageDraw object
font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
image = Image.new("L", (WIDTH, HEIGHT), color="white")
draw = ImageDraw.Draw(image)

# Draw time
time_str = datetime.datetime.now().strftime("%H:%M")
time_width, time_height = draw.textsize(time_str, font=font)
draw.text(((WIDTH - time_width) / 2, 0), time_str, font=font, fill=FONT_COLOR)
time_width, time_height = draw.textsize(time_str, font=font)

# Draw date
time_str = datetime.datetime.now().strftime("%A %-d %B %Y")
font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE / 5 ) )
date_width, date_height = draw.textsize(time_str, font=font)
draw.text(((WIDTH - date_width) / 2, time_height + 10 ), time_str, font=font, fill=FONT_COLOR)
line_y = time_height + date_height + 20

# Get weather data
weather_age = ( time.time() - os.path.getmtime( WEATHER_FILE ) ) / 60
if not os.path.isfile( WEATHER_FILE ) or weather_age > 10:
  
  # Cache the weather
  url = 'https://weather-broker-cdn.api.bbci.co.uk/en/forecast/aggregated/' + str(BBC_WEATHER_LOCATION_ID)
  weather = requests.get(url).json()
  open( WEATHER_FILE, 'w' ).write(json.dumps(weather))
else:
  weather = json.loads( open( WEATHER_FILE, 'r' ).read() )

# Just get the next 8 hours
reports = []
for report in weather['forecasts'][0]['detailed']['reports']:
  if len( reports ) >= 8: break
  reports.append( report )

# Draw weather
i=1
spacing = int( WIDTH/(len(reports)+1) )
font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE / 12 ) )
ICON_SIZE = 40
for r in reports:
  x = (i*spacing) 

  # Weather icon
  icon = Image.open('icons/' + str( r['weatherType'] ) + '.png').convert('L').resize((ICON_SIZE,ICON_SIZE))
  image.paste(icon,(x-int(ICON_SIZE/2),line_y))
  
  # Temperature and precipitation
  temp_and_precip = str( r['temperatureC'] ) + '° ' + str( r['precipitationProbabilityInPercent'] ) + '%'
  width, height = draw.textsize( temp_and_precip, font=font)
  draw.text((x-int(width/2),line_y+ICON_SIZE), temp_and_precip, font=font, fill=FONT_COLOR)

  # Time slot
  width, height = draw.textsize( r['timeslot'], font=font)
  draw.text((x-int(width/2),line_y+ICON_SIZE+height), r['timeslot'], font=font, fill=FONT_COLOR)
  i+=1
  # print( report )
  # print(report['timeslot'],report['weatherType'],report['temperatureC'],report['precipitationProbabilityInPercent'])
line_y += 90

# Load event data from vCalendar file
with open(EVENTS_FILE, "r") as f:
  c = Calendar(f.read())
  events = []
  running = []
  imminent = []
  comingup = []
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

# print(json.dumps(events,indent=2))

def draw_block( title, titlesize, items ):
  global line_y, margin
  if len( items ) == 0: return
  items = sorted(items, key=lambda x: x['date'] + x['start'])

  # Title
  font = ImageFont.truetype(FONT_PATH, titlesize)  
  title_width, title_height = draw.textsize( title, font=font)
  draw.text((margin, line_y), title, font=font, fill=FONT_COLOR)

  # Number of mins til start
  font = ImageFont.truetype(FONT_PATH, int( FONT_SIZE/6 ))
  starting = int( ( items[0]['start_timestamp'] - time.time() ) / 60 )
  subtitle = ''
  if starting > 0:
    subtitle = 'in ' + str( starting ) + ' mins'
  else:
    subtitle = str(-1*starting) + ' mins ago'
  subtitle_width, subtitle_height = draw.textsize( title, font=font)
  draw.text((margin, title_height + line_y), subtitle, font=font, fill=FONT_COLOR)
    
  # List events
  txt = []
  for event in items:
    txt.append( '\n'.join( textwrap.wrap( event["name"], width=30 ) ) )
  txt = '\n'.join(txt)
  font = ImageFont.truetype(FONT_PATH, int(FONT_SIZE/6))  
  width, height = draw.textsize( txt, font=font)
  draw.text((int(WIDTH*0.35) + 10, line_y), txt, font=font, fill=FONT_COLOR)
  line_y += max( title_height + subtitle_height, height ) + 30
  
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
for event in events:

    if day != event['date']:
      date_width, date_height = draw.textsize( event['date_str'], font=date_font)
      draw.text( ( margin, line_y), event['date_str'], font=date_font)
      line_y += date_height
      day = event['date']

    start_text = f'{event["start"]}'
    end_text = f'{event["end"]} ({event["duration"]})'
    event_text = '\n'.join( textwrap.wrap( event["name"], width=50 ) )
    start_width, start_height = draw.textsize( start_text, font=start_font)
    end_width, end_height = draw.textsize( end_text, font=end_font)
    event_width, event_height = draw.textsize( event_text, font=event_font)
    if line_y + event_height > HEIGHT:
        break
    draw.text((margin, line_y), start_text, font=start_font, fill=FONT_COLOR)
    draw.text((margin, line_y+start_height), end_text, font=end_font, fill=FONT_COLOR)
    draw.text((margin+start_width+10, line_y + 10), event_text, font=event_font, fill=FONT_COLOR)
    line_y += start_height + end_height + 20

# Save image to file
image.save("clock.png")

