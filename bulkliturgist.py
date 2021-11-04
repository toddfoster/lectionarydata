#!/usr/bin/env python3
"""Bulk Liturgist

Produce liturgies for a particular year based on the liturgical
calendar from the Book of Common Prayer (1979) for Sundays and
Major Feasts.

Required data sources are:
 - calcdates.json: info on how to calculate the calendar dates
   of Sundays & major feasts
 - bcpcollects.json: source of proper titles for Sundays/feasts
 - templatesdir : source of templates for how to generate each
   liturgy

Usage
  bulkliturgist [year] [flags...]
  year = numeric year (e.g., 2022 will generate liturgies from
         Advent 1 (28 Nov 2021) through Proper 29/CTK (20 Nov 2022).
         Defaults to current year according to the liturgical
         calendar.

Flags
 - --dry-run : don't write anything to disk
 - --past -p : generate liturgies even for dates already past
 - --templates -t dir : directory for templates
 - --output -o dir : directory for output
 - --day -d day : code for liturgical day to generate
 - --help -h : command-line options
 - --usage : more information

Templates
  A template is chosen by looking in subdirectories of the templates
  directory in order:
     - a directory named for the year (e.g., 2022)
     - yeara | yearb | yearc
     - default

  Inside each subdirectory, we look for a file named (in order):
     - with the code for the day (e.g., "first-sunday-of-advent.txt")
     - with the season for the day: 'advent.txt | christmas.txt |
       epiphany.txt | lent.txt | easter.txt | proper.txt
     - default.txt

  The first appropriate file found is used.

The liturgies output, as origianlly implemented, are used to
populate the website https://www.sharedprayers.net using
the static website generator hugo (https://www.gohugo.io).
"""

copyright = """Copyright 2021 Todd Foster

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from dateutil.easter import *
from dateutil.relativedelta import *
from datetime import *
import calendar
import json
from pathlib import Path
import os
import argparse

# Important data files
# https://github.com/toddfoster/sharedprayers/tree/master/data
calcdatesfile = 'output/calcdates.json'
collectsfile = 'output/bcpcollects.json'

# Default directories
templatesdir = "src/templates"
outputdir = "output/2022"

####################################################
####################################################
"""
argparse:
https://docs.python.org/3/library/argparse.html#module-argparse
https://docs.python.org/3/howto/argparse.html
"""
parser = argparse.ArgumentParser()
parser.add_argument('year', help='Year to generate (beginning from Advent 1 of previous calendar year).')
parser.add_argument('--dry-run', action="store_true", help="don't write anything to disk")
parser.add_argument('-p', '--past', action="store_true", help="generate liturgies even for dates already past")
parser.add_argument('-d', '--day', type=str, help='specific day code to generate (e.g., first-sunday-of-advent)')
parser.add_argument('--usage', action="store_true", help="more usage information")
parser.add_argument('--copyright', action="store_true", help="show copyright info")
parser.add_argument('--templates', type=str, help='templates directory')
parser.add_argument('--output', type=str, help='output directory')

args = parser.parse_args()

if args.usage:
    print(__doc__)
    sys.exit(0)

if args.copyright:
    print(copyright)
    sys.exit(0)

skip_past_dates = not args.past
dry_run = args.dry_run
only_day = args.day
if args.templates:
    templatesdir = args.templates
if args.output:
    outputdir = args.output
year = args.year
####################################################
####################################################

calcdates = []
with open(calcdatesfile, "r") as f:
    data = f.read()
    calcdates = json.loads(data)

collects = []
with open(collectsfile, "r") as f:
  data = f.read()
  collects = json.loads(data)

def sundayafterchristmas(year):
  return date(year,12,26) + relativedelta(weekday=calendar.SUNDAY)

def sundayafterepiphany(year):
  return date(year,1,7) + relativedelta(weekday=calendar.SUNDAY)

def getrecord(data, day):
  for i in data:
    if i['day'] == day:
      return i

def liturgydate(day, year):
  """
  Calculate the calendar date for a liturgy in a liturgical year.

  Liturgical year begins on Advent 1 (fourth Sunday before
  Christmas). So liturgydate('first-sunday-of-advent', 2022)
  returns "2021-11-28".
  """
  year = int(year)

  # special case: thanksgiving-day on fourth Thursday in November
  if day == 'thanksgiving-day':
    return date(year,11,22) + relativedelta(weekday=calendar.THURSDAY)

  calculator = getrecord(calcdates, day)
  if not calculator:
    raise Exception ("Calculation data for day " + day + " not found.")
  method = calculator['relative']
  value = calculator['value']

  # methods = ["xmas-last", "date", "eiphany1", "easter", "xmas-next"]
  if method == 'xmas-last':
    return sundayafterchristmas(year-1) + relativedelta(days=int(value))

  if method == 'xmas-next':
    return sundayafterchristmas(year) + relativedelta(days=int(value))

  if method == 'epiphany1':
    return sundayafterepiphany(year) + relativedelta(days=int(value))

  if method == 'easter':
    return easter(year) + relativedelta(days=int(value))

  if method == 'date':
    when = date.fromisoformat(value)
    when = date(year, when.month, when.day)
    # correct for static dates that occur between advent 1 & turn of year
    if when > liturgydate('first-sunday-of-advent', year+1):
      when = date(year-1, when.month, when.day)
    return when

  raise Exception("Invalid method encountered: " + method)

def lectionarytitle(day, year):
  collect = getrecord(collects, day)
  if not collect:
    raise Exception ("Title or day " + day + " not found.")
  return collect['title']

def lectionaryyear(year):
  # Working backwards, 1900 would be year a!
  year = int(year)
  if year < 1900:
    raise Exception ("Invalid year " + str(year) + ": only 1900 and later are supported.")
  year = (year - 1900) % 3
  if year == 0: return 'a'
  elif year == 1: return 'b'
  else: return 'c'

def header(day, year):
  result = "---\n"
  result += "title: " + lectionarytitle(day, year) + "\n"
  result += "date: " + str(liturgydate(day, year)) + "\n"
  result += "lectionaryyear: " + lectionaryyear(year) + "\n"
  result += "proper: " + day + "\n"
  return result

def choosetemplateindir(day, year, directory):
  directory = templatesdir + "/" + directory
  candidate = Path(directory + "/" + day + ".txt")
  if candidate.is_file(): return candidate

  for s in ('advent', 'christmas', 'epiphany', 'lent', 'easter', 'proper'):
    if day.find(s) >= 0:
      candidate = Path(directory + "/" + s + ".txt")
      if candidate.is_file(): return candidate

  candidate = Path(directory + "/" + "default" + ".txt")
  if candidate.is_file(): return candidate

  return ""

def choosetemplate(day, year):
  """
  Selects a template for the given liturgy

  Parameters
  ----------
  day : str
      The code for the day (e.g., first-sunday-of-advent)

  year : str
      The liturgical year. Days from first advent through the
      end of the year go with the following liturgical year.
      E.g., first-sunday-of-advent for year = 2022 occurs on
      28 November 2021. (This could also be passed as an int.)

  Chooses a template by looking in subdirectories of templatesdir,
  in order:
     - a directory named for the year (e.g., 2022)
     - yeara | yearb | yearc
     - default

  Inside each subdirectory, we look for a file named (in order):
     - with the code for the day (e.g., "first-sunday-of-advent.txt")
     - with the season for the day: 'advent.txt | christmas.txt |
       epiphany.txt | lent.txt | easter.txt | proper.txt
     - default.txt

  As soon as an appropriate file is found, its path/name is returned.
  """
  year = str(year)

  c = choosetemplateindir(day, year, year)
  if c: return str(c)

  c = choosetemplateindir(day, year, "year" + lectionaryyear(year))
  if c: return str(c)

  c = choosetemplateindir(day, year, "default")
  return str(c)

def generateliturgy(day, year):
  result = header(day, year)
  template = choosetemplate(day, 2022)
  with open(template, "r") as f:
    for line in f:
      result += line
  return result

def writeliturgy(day, when, year):
    if only_day and only_day != day:
      return

    if dry_run:
      print ("DRY RUN: Not writing liturgy for " + day + ": " + str(when))
      return

    print ("Writing liturgy for " + day + ": " + str(when))
    liturgy = generateliturgy(day, year)
    with open (outputdir + "/" + day + ".md", "w") as t:
      t.write(liturgy)
      t.write("\n")

def majorliturgies(year):
  """
  Generate liturgies for Sundays and major feasts.
  """
  if not dry_run:
    os.makedirs(outputdir, exist_ok=True)

  year = int(year)

  for d in calcdates:
    dday = d['day']
    ddate = liturgydate(dday, year)

    # skip past dates?
    if skip_past_dates:
      if ddate < date.today():
        continue

    # skip second-sunday-after-christmas if it occurs after the-epiphany
    if dday == 'second-sunday-after-christmas':
      if ddate > date(year,1,6):
        continue

    # skip epiphanies that happen on or after last-sunday-after-the-epiphany
    # exploiting a fortuitous difference to not skip last-sunday-after-THE-epiphany
    if dday.find('after-epiphany') >= 0:
      if ddate >= liturgydate('last-sunday-after-the-epiphany', year):
        continue

    # skip propers that happen on or before trinity-sunday
    if dday.find('proper') >= 0:
      if ddate <=  liturgydate('trinity-sunday', year):
        continue

    writeliturgy(dday, ddate, year)

  # Add thanksgiving-day, which is not included in calcdates.json
  thanksgivingdate = liturgydate('thanksgiving-day', year)
  if thanksgivingdate > date.today() or not skip_past_dates:
    writeliturgy('thanksgiving-day', thanksgivingdate, year)

majorliturgies(year)
