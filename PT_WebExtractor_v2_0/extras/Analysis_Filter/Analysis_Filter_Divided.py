import os
import sys
import codecs
import csv
import re
import collections
import argparse
import json
import ast
import traceback
import inflect
import Tkinter, Tkconstants, tkFileDialog
from openpyxl import *
from openpyxl.styles import *
from openpyxl.worksheet.write_only import WriteOnlyCell
#from methods import xl_methods as xl

home_folder = os.path.abspath(os.path.join(__file__, "..\\..\\.."))
scripts_folder = os.path.join(os.sep, home_folder, 'scripts')
sys.path.append(scripts_folder)

from common import shared
from common import spreadsheet as sh

def get_groups(in_csv):
	srch_csv = open(in_csv, mode='rb')
	srch_lines = srch_csv.readlines()
	
	groups = []
	
	for line in srch_lines[1:]:
		line_parse = line.split(',')
		group = line_parse[0]
		group = group.strip()
		if not group == '':
			groups.append(group)
	
	groups = list(set(groups))
	
	return groups

def get_word_list(words, juris, omit=False):

	# Create the inflect engine to get plurals
	p = inflect.engine()
	
	# First, remove any blanks in the list
	words = [word for word in words if not word.strip() == '']

	if omit:
		singular_words = [word.strip()[1:] for word in words if word[0] == '-']
	else:
		singular_words = [word.strip() for word in words if not word[0] == '-']
		
	#print singular_words
	if not juris == 'Quebec':
		plural_words = [p.plural(word) for word in singular_words]
		srch_words = singular_words + plural_words
	else:
		srch_words = singular_words
	
	return srch_words
	
def get_search_words(juris, group='gb3', kword_fn=None):
	# Get the list of search words from a CSV file
	if kword_fn is not None:
		srch_csv = codecs.open(kword_fn, encoding='utf-8', mode='rb')
	else:
		srch_csv = open('files\\filter_lists.csv', mode='rb')
	srch_lines = srch_csv.readlines()
	srch_words = collections.OrderedDict()
	
	for line in srch_lines[1:]:
		# Each line in the filter list CSV file contains:
		#	- first column is the group name
		#	- second column is the theme name
		#	- last column contains the keywords
		# Ex: GB3,Imagery,[imagery,uav,drone,ortho]
		
		line = line.strip()
		
		if line == '': continue
		
		# Parse the square brackets
		quotes = []
		start_pos = line.find('"')
		while start_pos > -1:
			end_pos = line.find('"', start_pos+1)
			quote = line[start_pos+1:end_pos]
			quotes.append(quote)
			start_pos = line.find('"', end_pos+1)
			
		if len(quotes) == 0: continue
			
		# Split and strip keywords
		keywords = []
		for k in quotes:
			out_k = k.split(',')
			out_k = [k.strip() for k in out_k]
			keywords.append(out_k)
		
		vals = line.split(',')
		
		group_val = vals[0]
		theme = vals[1]
		
		print "group: %s" % group
		print "group_val: %s" % group_val
		if not group == 'all':
			if group_val.lower().find(group.lower()) > -1:
				srch_words[theme] = keywords
		else:
			srch_words[theme] = keywords
			
	print "srch_words: %s" % srch_words
		
	return srch_words
	
def search_dataset(row, idx, words):

	out_lines = []
	found_idx = []
	
	title_str = row['Title'].lower().replace('_', ' ')
	desc_str = row['Description'].lower()

	if search_text(title_str, words):
		
		# Add the line to the filtered list
		out_lines.append(('title', row))
		
		# Add the line index to the found_idx list
		found_idx.append(idx)
		
	elif search_text(desc_str, words):
		
		# Add the line to the filtered list
		out_lines.append(('desc', row))

		# Add the line index to the found_idx list
		found_idx.append(idx)
		
	return (out_lines, found_idx)
	
def search_text(text, words):

	return any(re.compile(r'\b' + kyword + r'\b').search(text) for kyword in words)

def run(juris, xl_fn, group, place='', keywords=None):

	juris = juris.replace(' ', '_')
	
	os.system("title Analysis Filter - %s" % juris)
	
	# Open merged spreadsheet
	#print "#1"
	merged_xl = sh.PT_XL(fn=xl_fn, read_only=True)
	#print "#2"
	merged_xl.set_workbook()
	merged_xl.set_worksheet('Merged Datasets')
	in_rows = merged_xl.get_dictrows('values')
	header_txts = in_rows[0].keys()
	
	#print list(in_rows)
	
	#answer = raw_input("Press enter...")
	
	# Get a list of search words from the filter CSV file
	srch_words = get_search_words(juris, group, keywords)
	
	if not srch_words:
		print "No search words for that group."
		merged_xl.close_workbook()
		return None
	
	#answer = raw_input("Press enter...")
	
	out_lines = collections.OrderedDict()
	
	found_idx = []
	
	# Create the inflect engine to get plurals
	p = inflect.engine()
	
	#print srch_words
	
	#answer = raw_input("Press enter...")
	
	for k, words in srch_words.items():
		# Go through each list of words
		
		print words
		
		#answer = raw_input("Press enter...")
		
		filtered_lines = []
		
		for idx, row in enumerate(in_rows):
			msg = "Filtering %s of %s lines for search words" % (idx + 1, len(in_rows))
			shared.print_oneliner(msg)
			
			# Go through each line in the merged CSV
			if row['Source'] == 'err_log.csv': continue
			
			#print "k: %s" % k
			#row['Layer'] = k
			#row['P/T'] = shared.get_pt_abbreviation(juris)
			
			title_str = row['Title'].lower().replace('_', ' ')
			desc_str = row['Description'].lower()
			
			if place is None or place == '':
			
				if len(words) > 1:
					# If there is a 2nd filter, use it to narrow searches
					filter2 = words[1]
					if search_text(title_str, filter2) or \
						search_text(desc_str, filter2):
						
						print
						print
						print title_str
						print
						print desc_str
						
						answer = raw_input("Press enter...")
						
						cur_lines, cur_found = search_dataset(row, idx, words[0])
						
						filtered_lines += cur_lines
						found_idx += cur_found
				else:
					cur_lines, cur_found = search_dataset(row, idx, words[0])
					
					filtered_lines += cur_lines
					found_idx += cur_found
			else:
				if desc_str.lower().find(place.lower()) > -1:
					if len(words) > 1:
						filter2 = words[1]
						if search_text(title_str, filter2) or \
							search_text(desc_str, filter2):
							
							cur_lines, cur_found = search_dataset(row, idx, words[0])
							
							filtered_lines += cur_lines
							found_idx += cur_found
					else:
						cur_lines, cur_found = search_dataset(row, idx, words[0])
						
						filtered_lines += cur_lines
						found_idx += cur_found					
		print
		
		# Add the filtered lines to the out_lines with the current theme as key
		out_lines[k] = filtered_lines
		
		#print "Out lines: %s" % out_lines[k]
	
		#answer = raw_input("Press enter...")
	
	out_f = codecs.open('out_tmp.txt', encoding='utf-8', mode='w')
	
	# Set the widths of each column in the output
	# header_info = [('Layer', 24), ('P/T', 6), ('Source', 50), 
				# ('Title', 100), ('Description', 100), 
				# ('Type', 20), ('Start Date', 20), ('Recent Date', 20), 
				# ('Update Frequency', 35), ('Publisher', 60), 
				# ('Licensing', 50), ('Available Formats', 50), 
				# ('Access', 32), ('Download', 25), ('Spatial Reference', 50), 
				# ('Data URL', 70), ('Web Page URL', 70), 
				# ('Web Map URL', 70), ('Service', 25), 
				# ('Service Name', 100), ('Service URL', 70), 
				# ('Metadata URL', 70), ('Metadata Type', 65), 
				# ('Notes', 100)]
	header_info = sh.get_header_info('analysis')['xl']
	
	#print header_info
	#answer = raw_input("Press enter...")
	
	try:
		# Open the output CSV file for editing
		if place == '' or place is None:
			outxl_fn = "results\\%s\\%s_%s_results.xlsx" % (juris, juris, \
															group.upper())
		else:
			outxl_fn = "results\\%s\\%s_%s_%s_results.xlsx" % (juris, juris, \
															place, group.upper())
		
		# Create the Excel file
		# out_xl = sh.PT_XL(fn=outxl_fn, write_only=True, 
		# 					replace=True, replace_ws=True)
		#print "#3"
		out_xl = sh.PT_XL(fn=outxl_fn, replace=True, replace_ws=True)
		#print "#4"
	
		for word, value in out_lines.items():
		
			# Go through each theme's output lines
			
			theme_wsname = '%s' % word.title()
			
			#desc_wsname = 'Found in Descriptions'
			theme_ws = out_xl.add_worksheet(theme_wsname, header_info, \
								'Found in Titles')
			
			keywords_str = ', '.join(srch_words[word][0])
			out_xl.write_cell(3, 1, 'Keywords: %s' % keywords_str)
			
			titles = [v[1] for v in value if v[0] == 'title']
			descs = [v[1] for v in value if v[0] == 'desc']
			
			for idx, title in enumerate(titles):
				msg = "Saving %s of %s lines to '%s'" % \
						(idx + 1, len(titles), outxl_fn)
				shared.print_oneliner(msg)
				
				# Convert the current line dictionary to cells
				title['Layer'] = word
				title['P/T'] = shared.get_pt_abbreviation(juris)
				for k, v in title.items():
					out_xl.add_cell(v, k)
				
				out_xl.write_row()
				
			print
				
			out_xl.write_row()
			
			out_xl.add_title('Found in Description', (1, 2))
			
			out_xl.add_header()
			
			for idx, desc in enumerate(descs):
				msg = "Saving %s of %s lines to '%s'" % \
						(idx + 1, len(descs), outxl_fn)
				shared.print_oneliner(msg)
				
				# Convert the current line dictionary to cells
				desc['Layer'] = word
				desc['P/T'] = shared.get_pt_abbreviation(juris)
				for k, v in desc.items():
					out_xl.add_cell(v, k)
				
				out_xl.write_row()
			
			print
		
		# Add the other datasets
		# This has been removed for now
		
		# other_ws = out_xl.add_worksheet('Others', header_info)
		
		# found_idx = list(set(found_idx))
		# print "Number of indices: %s" % len(found_idx)
		# print "Number of lines: %s" % len(in_rows)
		
		# for idx, item in enumerate(in_rows):
			# if idx not in found_idx:
				# item['Layer'] = 'N/A'
				# item['P/T'] = shared.get_pt_abbreviation(juris)
				# for k, v in item.items():
					# out_xl.add_cell(v, k)
					
				# out_xl.write_row()
		
		# save the file
		out_xl.save_file()
		
		merged_xl.close_workbook()
			
	except Exception, e:
		print e
		traceback.print_exc(file=sys.stdout)
		#out_f.write(unicode(in_line))
		#out_f.write('\n')
		answer = raw_input("Press enter...")
	
	####################################################################
	# Create an XLSX file with unknown classifications
	
	# other_csv_fn = "results\\%s\\_%s_%s_other_results.xlsx" % (juris, \
					# juris, group.upper())
	
	# # Create the other Excel file
	# other_xl = sh.PT_XL(fn=other_csv_fn, write_only=True, 
						# replace=True, replace_ws=True)
	
	# wsname = 'Other Datasets'
	# title_ws = other_xl.add_worksheet(wsname, header_info)
	
	# for idx, line in enumerate(in_rows):
	
		# msg = "Saving %s of %s other lines" % (idx + 1, len(in_rows))
		# #print msg
		# shared.print_oneliner(msg)
	
		# if idx == 0:
			# #print "idx is zero!"
			# continue
	
		# if line['Source'] == 'err_log.csv' or line['Source'] == 'URL':
			# #print "Source is invalid!"
			# continue
		
		# # if idx not in found_idx:
			# # vals = [line[key] for key in header_txts]
			# # other_xl.write_list(vals, wsname)
		
		# if idx not in found_idx:
			# line['Layer'] = '%s_other' % group.upper()
			# line['P/T'] = shared.get_pt_abbreviation(juris)
			# for k, v in line.items():
				# other_xl.add_cell(v, k)
				
			# other_xl.write_row()
			
	# print
			
	# # save the file
	# other_xl.save_file()
	
	out_f.close()
	#csv_f.close()

def main():
	try:
		parser = argparse.ArgumentParser()
		parser.add_argument("-j", "--jurisdiction", help="The province or territory to be extracted.",
							metavar="Province or Territory")
		parser.add_argument("-g", "--group", help="The group name (ex: GB3) for the output.",
							metavar="Layer")
		parser.add_argument("-p", "--place", help="The place name used to narrow the results.",
							metavar="Place Name")
		parser.add_argument("-k", "--keywords", help="The file containing the keywords.",
							metavar="Keywords File")
		args = parser.parse_args()

		juris = args.jurisdiction
		keywords = args.keywords
		group = args.group
		place = args.place
		
		if juris is None:
			answer = raw_input("\nPlease enter a province or territory for extraction (full name or 2-letter "
							   "abbreviation): ")
			if not answer == "":
				juris = answer.lower()
			else:
				print "\nERROR: Please specify a province or territory."
				print "Exiting process."
				sys.exit(1)
				
		if juris.lower() == 'alberta' or juris.lower() == 'ab':
			juris = 'Alberta'
		elif juris.lower() == 'british columbia' or juris.lower() == 'bc':
			juris = 'BC'
		elif juris.lower() == 'manitoba' or juris.lower() == 'mb':
			juris = 'Manitoba'
		elif juris.lower() == 'new brunswick' or juris.lower() == 'nb':
			juris = 'New Brunswick'
		elif juris.lower().find('newfoundland') > -1 or juris.lower().find('labrador') > -1 or juris.lower() == 'nl':
			juris = 'NL'
		elif juris.lower() == 'nova scotia' or juris.lower() == 'ns':
			juris = 'Nova Scotia'
		elif juris.lower() == 'nunavut' or juris.lower() == 'nu':
			juris = 'Nunavut'
		elif juris.lower().find('northwest') > -1 or juris.lower() == 'nt':
			juris = 'NWT'
		elif juris.lower() == 'ontario' or juris.lower() == 'on':
			juris = 'Ontario'
		elif juris.lower().find('edward') > -1 or juris.lower() == 'pe':
			juris = 'PEI'
		elif juris.lower() == 'quebec' or juris.lower() == 'qc':
			juris = 'Quebec'
		elif juris.lower() == 'saskatchewan' or juris.lower() == 'sk':
			juris = 'Saskatchewan'
		elif juris.lower() == 'yukon' or juris.lower() == 'yt' or juris.lower() == 'yk':
			juris = 'Yukon'
		elif juris.lower() == 'all':
			juris = 'all'
		elif answer.lower() == 'help' or answer.lower().find('h') > -1:
			parser.print_help()
			sys.exit(1)
		else:
			print "\nERROR: '%s' is not a valid province or territory."
			print "Exiting process."
			sys.exit(1)
			
		# Get the file with keywords from the user
		script_path = os.path.abspath(__file__)
		init_dir = os.path.dirname(script_path) + "\\files"
		
		if keywords is None:
			root = Tkinter.Tk()
			root.withdraw()
			keywords = tkFileDialog.askopenfilename(initialdir=init_dir, \
								title="Select Keywords File", \
								filetypes=(("CSV files", "*.csv"), 
											("All files", "*.*")))
											
		# If the file does not exist or the user did not enter it,
		#	use the default
		if keywords is None or not os.path.exists(keywords):
			keywords = 'files\\filter_lists.csv'
			# ****** NOTE: add French file for Quebec later **********
		
		# Get a list of available groups from the file
		group_lst = get_groups(keywords)
		
		avail_grps = '\n - '.join(group_lst)
		
		print group_lst
		
		if group is None:
			print '''
Available Group Options:
 - %s
 - all''' % avail_grps
			answer = raw_input("Please enter a group for extraction from the above options [all]: ")
			if not answer == "":
				group = answer.lower().replace(' ', '_')
			else:
				group = 'all'
		
		avail_grps_lower = [g.lower() for g in group_lst]
		
		if not group.lower() == 'all' and not group.lower() in avail_grps_lower:
			print "Please specify a group from the available options."
			print "Exiting process."
			sys.exit(1)
			
		if place is None:
			answer = raw_input("Please enter a place name to narrow the location of the results: ")
			if not answer == "":
				place = answer.lower()

		res_folder = shared.get_results_folder()
		if group == 'all':
			groups = group_lst
		else:
			groups = [group]
			
		for grp in groups:
			if juris == 'all':
				pt_folders = shared.get_pt_folders()
				for pt in pt_folders:
					juris = os.path.basename(pt.strip('\\'))
					if not juris == "Canada":
						print "\nRunning Analysis for %s" % juris
						xl_fn = os.path.join(os.sep, pt, "_%s_merged.xlsx" % juris)
						run(juris, xl_fn, grp, place, keywords)
			else:
				juris = juris.replace(' ', '_')
				xl_fn = os.path.join(os.sep, res_folder, juris, \
										"_%s_merged.xlsx" % juris)
				run(juris, xl_fn, grp, place, keywords)
		
		print "\nFilter completed successfully."

	except Exception, err:
		print 'ERROR: %s\n' % str(err)
		print traceback.format_exc()

if __name__ == '__main__':
	sys.exit(main())