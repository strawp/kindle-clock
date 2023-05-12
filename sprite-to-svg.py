import re, subprocess

# Converts an SVG doc containing a number of symbols and turns them into individual PNG renderings of that symbol

icons = open('icons.svg','r').read()
m = re.findall(r'<symbol([^>]*)>(.*?)<\/symbol>', icons)
for i in m:
  try:
    name = str(int(re.search(r'id="wr-icon-weather-type--([0-9]+)"',i[0]).group(1))) + ".svg"
  except:
    continue
  print( name )
  svg = f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" {i[0]}><g>{i[1]}</g></svg>'
  open( name, 'w' ).write( svg )
  subprocess.check_output(['convert',name,name.replace('.svg','.png')])



