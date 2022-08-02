#!/Users/mlautman/virtual_python_environment/bin/python3.9
#
# How to run this report:
#
# 1  Configuration > Robots.txt > Settings > Ignore robots.txt
# 1. Start a screaming frog job.
# 2. After the job finishes, Bulk Export > Links > All Outlinks.
# 3. Run screaming_frog.py.
import csv
import sys
import getopt
import os
import shutil
import re


def command_line_args(argv):
	full_helptext = "\nUsage: screaming_frog.py [-2] [-s] [-f] [-t] [-h]\n" + "\n-2 Include rows with status code 200, otherwise remove those rows.\n\n" + "-s include a Screaming Frog scan, otherwise do not do the scan (and assume the results are in /tmp/cli/all_outlinks.csv)\n\n" + "-f Include all source URLs, otherwise retain only those that start with https://www.brightspot.com/documentation/\n\n" + "-t Include only links in the topic (excludes links in TOC, left nav, footer\n\n" + "-h Display this help text.\n"
	try:
		optlist, csvfile = getopt.getopt(argv,'2fhst')
	except getopt.GetoptError as err:
		print("Unrecognized option\n")
		print (full_helptext)
		sys.exit()
	global include_200
	global retain_all_sources
	global include_sf_run
	global topic_links_only
	for opt,arg in optlist:
		if opt == '-h':
			print (full_helptext)
			sys.exit()
		elif opt == '-2':
				include_200 = True
		elif opt == '-f':
				retain_all_sources = True
		elif opt == '-s':
				include_sf_run = True
		elif opt == '-t':
				topic_links_only = True
		
	print("Running with the following options:")
	print("  Include status code 200: " + str(include_200))
	print("  Include non-documentation sources: " + str(retain_all_sources))
	print("  Include Screaming Frog run: " + str(include_sf_run))
	print("  Include topic links only: " + str(topic_links_only))

include_200 = False
retain_all_sources = False
include_sf_run = False
topic_links_only = False

command_line_args(sys.argv[1:])

if include_sf_run:
# If we include the Screaming Frog run, create directories for the SF output and then run the SF command.
	configuration_file_path = "/Users/mlautman/Documents/support_desk/quality_problems/broken_links_brightspot_15_2url_per_second.com.seospiderconfig"
	if not os.path.exists(configuration_file_path):
		print("Missing the configuration file broken_links_brightspot.com.seospiderconfig. Exiting.")
		sys.exit()

	print("Creating output directory")

	if os.path.lexists("/tmp/cli/"):
		shutil.rmtree("/tmp/cli/", ignore_errors=True)

	os.mkdir("/tmp/cli")

	command_line = '"/Applications/Screaming Frog SEO Spider.app/Contents/MacOS/ScreamingFrogSEOSpiderLauncher" --crawl https://brightspot.com --headless --save-crawl --output-folder /tmp/cli --bulk-export "Links:All Outlinks" --export-format csv --config {}'.format(configuration_file_path)

	os.system(command_line)

else:
# If we do not include the Screaming Frog run, ensure that its output exists.
	if not os.path.exists("/tmp/cli/all_outlinks.csv"):
		print("\nMissing the output file /tmp/cli_outlinks.csv from a Screaming Frog run. Rerun this command with the -s option to generate it. Exiting.")
		sys.exit()

print("Processing /tmp/cli/all_outlinks.csv")

path_to_csv_file = "/tmp/cli/all_outlinks.csv"

uniques = set({})
counters = {
	'lines_duplicates' : 0,
	'lines_excluded' : 0,
	'lines_in_file' : 1,
	'lines_output' : 0
}
csvfile = open(path_to_csv_file,mode='r',encoding='utf-8-sig')
ods_import = open('/tmp/cli/ods_import.csv','w')
linkreader = csv.DictReader(csvfile,delimiter=',')
linkwriter = csv.writer(ods_import,delimiter=',')
line = next(linkreader);
linkwriter.writerow(['Type','Source','Destination','Anchor','Status Code','Status'])
for row in linkreader:
	counters['lines_in_file'] += 1
	if (retain_all_sources == True or \
		(retain_all_sources == False and row['Source'].startswith('https://www.brightspot.com/documentation/'))) and \
		(include_200 == True or \
		(include_200 == False and row['Status Code'] != '200')) and \
		(topic_links_only == False or \
		(topic_links_only == True and row['Link Path'].find('SupportDeskTopicPage-main') != -1)):

		unique_key = row['Source'] + row['Destination']
		if unique_key not in uniques:
			uniques.add(unique_key)
			linkwriter.writerow([row['Type'],row['Source'],row['Destination'],row['Anchor'],row['Status Code'],row['Status']])
			counters['lines_output'] += 1
		else:
			counters['lines_duplicates'] += 1
	else:
		counters['lines_excluded'] += 1
		
csvfile.close()
ods_import.close()

print("Creating SQLite import file")

csvfile = open(path_to_csv_file,mode='r',encoding='utf-8-sig')
csvline = 0;
pattern = re.compile(r'^"(.)(.*)(.)"$');
sqlite_import = open('/tmp/cli/sqlite_import.csv','w')
for line in csvfile:
	csvline += 1
	sqlite_string_1 = line.replace('","','*')
	sqlite_string_2 = sqlite_string_1.replace(',',' ')
	sqlite_string_3 = pattern.sub(f'\g<1>\g<2>\g<3>*{csvline}',sqlite_string_2)
	sqlite_string_4 = sqlite_string_3.replace('*',',')
	sqlite_import.write(sqlite_string_4)

sqlite_import.close()
print("\nResults:")
print("  Number of lines in file: {0:,}".format(counters['lines_in_file']))
print("  Number of excluded lines: {0:,}".format(counters['lines_excluded']))
print("  Number of duplicate lines: {0:,}".format(counters['lines_duplicates']))
print("  Number of lines output: {0:,}".format(counters['lines_output']))
print("ods import file is at '/tmp/cli/ods_import.csv'")
print("sqlite import file is at '/tmp/cli/sqlite_import.csv'")

print("Creating SQLite table and importing")
os.system('sqlite3 /Users/mlautman/Documents/support_desk/quality_problems/sqlite/ScreamingFrog.sqlite < /Users/mlautman/Documents/support_desk/quality_problems/sqlite/screaming_frog_commands.sql')

print("Creating HTML report")
htmlfile = open('/tmp/cli/broken_link_report.html',mode='w')
starting_string = """<!DOCTYPE html>
<html lang="en">
	<head>
		<title>Broken link report</title>
		<meta charset="utf-8"/>
		<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.3.1/dist/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
		<style>
			table {
				width: 100%;
				table-layout: fixed;
			}
			table td {
        		word-wrap: break-word;
      	}
			.comment {
				color: red;
				font-size: 120%;
			}
			td:first-child, th:first-child {
				width: 30%;
			}
			td:nth-child(2), th:nth-child(2) {
				width: 30%;
			}
			td:nth-child(3), th:nth-child(3) {
				width: 20%;
			}
			td:nth-child(4), th:nth-child(4) {
				width: 10%;
			}
			td:last-child, th:last-child {
				width: 10%;
			}
		</style>
	</head>
	<body class=p-5>
		<h1>Broken link report</h1>
		<table class="table">
		<thead>
			<tr>
				<th>Source</th>
				<th>Destination</th>
				<th>Link text</th>
				<th>Status code</th>
				<th>Status</th>
		</thead>
		<tbody>
			"""

ending_string = """			

		</tbody>
	</table>

	</body>
</html>"""
htmlfile.write(starting_string)
ods_import = open('/tmp/cli/ods_import.csv','r')
next(ods_import);
for row in ods_import:
	fields = row.split(',')
	detail = '\n<tr><td><a href="{0}">{0}</a></td><td><a href="{1}">{1}</a></td><td>{2}</td><td>{3}</td><td>{4}</td></tr>'.format(fields[1],fields[2],fields[3],fields[4],fields[5])
	htmlfile.write(detail)
htmlfile.write(ending_string)
htmlfile.close()
# in SQLITE
# sqlite3 /Users/mlautman/Documents/support_desk/quality_problems/sqlite/ScreamingFrog.sqlite

# Delete and recreate table; these commands are in /Users/mlautman/Documents/support_desk/quality_problems/sqlite/screaming_frog_commands.sql
# DROP TABLE screamingFrog;
# CREATE TABLE IF NOT EXISTS "screamingFrog" (
# type TEXT NOT NULL,
# source TEXT NOT NULL,
# destination TEXT NOT NULL,
# size INTEGER NOT NULL,
# altText TEXT,
# anchor TEXT,
# statusCode INTEGER NOT NULL,
# status TEXT NOT NULL,
# follow TEXT NOT NULL,
# target TEXT,
# rel TEXT,
# pathType TEXT NOT NULL,
# linkPath TEXT NOT NULL,
# linkPosition TEXT NOT NULL,
# linkOrigin TEXT NOT NULL,
# id INTEGER PRIMARY KEY NOT NULL UNIQUE
# );
# .mode csv
# .import --skip 1 /tmp/cli/sqlite_import.csv screamingFrog -- Imports into existing table;
# Erase table and recreate from import
# DROP TABLE screamingFrog;
# .import --csv /tmp/cli/sqlite_import.csv screamingFrog -- Creates the table from the CSV file.
# SELECT source,destination,statusCode FROM screamingFrog WHERE statusCode = 404 AND destination NOT LIKE '%introduction-to-dari' AND destination NOT LIKE '%theme-guide';
