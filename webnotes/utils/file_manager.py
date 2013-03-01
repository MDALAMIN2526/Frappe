# Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)
# 
# MIT License (MIT)
# 
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the "Software"), 
# to deal in the Software without restriction, including without limitation 
# the rights to use, copy, modify, merge, publish, distribute, sublicense, 
# and/or sell copies of the Software, and to permit persons to whom the 
# Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in 
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
# CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
# OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# 

from __future__ import unicode_literals
import webnotes
import os, conf
from webnotes.utils import cstr

class MaxFileSizeReachedError(webnotes.ValidationError): pass

def upload():
	# get record details
	dt = webnotes.form_dict.doctype
	dn = webnotes.form_dict.docname
	at_id = webnotes.form_dict.at_id
	file_url = webnotes.form_dict.file_url
	filename = webnotes.form['filedata'].filename
	
	webnotes.response['type'] = 'iframe'
	if not filename and not file_url:
		webnotes.response['result']	= """
		<script type='text/javascript'>
		window.parent.wn.views.fomrview['%s'].frm.attachments.dialog.hide();
		window.parent.msgprint("Please upload a file or copy-paste a link (http://...)");
		</script>""" % dt
		return
		
	# save
	if filename:
		fid, fname = save_uploaded()
	elif file_url:
		fid, fname = save_url(file_url)
		
	# save it in the form
	updated = False
	if fid:
		updated = add_file_list(dt, dn, fname, fid)
	
	if fid and updated:
		# refesh the form!
		# with the new modified timestamp
		webnotes.response['result'] = """
<script type='text/javascript'>
window.parent.wn.ui.form.file_upload_done('%(dt)s', '%(dn)s', '%(fid)s', '%(fname)s', '%(at_id)s', '%(mod)s');
window.parent.wn.views.formview['%(dt)s'].frm.show_doc('%(dn)s');
</script>
			""" % {
				'dt': dt,
				'dn': dn,
				'fid': fid,
				'fname': fname.replace("'", "\\'"),
				'at_id': at_id,
				'mod': webnotes.conn.get_value(dt, dn, 'modified')
			}

def save_uploaded():	
	webnotes.response['type'] = 'iframe'
	fname, content = get_uploaded_content()
	if content:
		fid = save_file(fname, content)
		# fname is not valid
		return fid, fid
	else: 
		return None, fname

def save_url(file_url):
	if not (file_url.startswith("http://") or file_url.startswith("https://")):
		webnotes.msgprint("URL must start with 'http://' or 'https://'")
		return None, None
		
	f = webnotes.doc("File Data")
	f.file_url = file_url
	f.file_name = file_url.split('/')[-1]
	f.save(new=1)
	return f.name, file_url

def get_uploaded_content():	
	# should not be unicode when reading a file, hence using webnotes.form
	if 'filedata' in webnotes.form:
		i = webnotes.form['filedata']
		webnotes.uploaded_filename, webnotes.uploaded_content = cstr(i.filename), i.file.read()
		return webnotes.uploaded_filename, webnotes.uploaded_content
	else:
		webnotes.msgprint('No File')
		return None, None

def save_file(fname, content, module=None):
	from webnotes.model.doc import Document
	from filecmp import cmp

	check_max_file_size(content)
	new_fname = write_file(content)

	# some browsers return the full path
	if '\\' in fname:
		fname = fname.split('\\')[-1]
	if '/' in fname:
		fname = fname.split('/')[-1]
		
	# we use - for versions, so remove them from the name!
	fname = fname.replace('-', '')

	fpath = os.path.join(get_files_path(), fname)
	if os.path.exists(fpath) and cmp(fpath, new_fname):
		# remove new file, already exists!
		os.remove(new_fname)
		return fname
	else:
		# generate the ID (?)
		f = Document('File Data')
		f.file_name = fname
		f.save(1)
		# rename new file
		os.rename(new_fname, os.path.join(get_files_path(), f.name))
		return f.name

def check_max_file_size(content):
	max_file_size = getattr(conf, 'max_file_size', 1000000)

	if len(content) > max_file_size:
		raise Exception, MaxFileSizeReachedError

def write_file(content):
	"""write file to disk with a random name (to compare)"""
	# create account folder (if not exists)
	webnotes.create_folder(get_files_path())
	fname = os.path.join(get_files_path(), webnotes.generate_hash())

	# write the file
	with open(fname, 'w+') as f:
		f.write(content)

	return fname	

def add_file_list(dt, dn, fname, fid):
	fl = webnotes.conn.get_value(dt, dn, 'file_list') or ''
	if fl: fl += '\n'
	fl += fname + ',' + fid
	webnotes.conn.set_value(dt, dn, 'file_list', fl)
	return True

def remove_all(dt, dn):
	"""remove all files in a transaction"""
	file_list = webnotes.conn.get_value(dt, dn, 'file_list') or ''
	for afile in file_list.split('\n'):
		if afile:
			fname, fid = afile.split(',')
			remove_file(dt, dn, fid)

def remove_file(dt, dn, fid):
	"""Remove fid from the give file_list"""
	
	# get the old file_list
	fl = webnotes.conn.get_value(dt, dn, 'file_list') or ''
	new_fl = []
	fl = fl.split('\n')
	for f in fl:
		if f and f.split(',')[1]!=fid:
			new_fl.append(f)

	# delete
	delete_file(fid)
		
	# update the file_list
	webnotes.conn.set_value(dt, dn, 'file_list', '\n'.join(new_fl))
	
	# return the new timestamp
	return webnotes.conn.get_value(dt, dn, 'modified')

def get_file_system_name(fname):
	# get system name from File Data table
	return webnotes.conn.sql("""select name, file_name from `tabFile Data` 
		where name=%s or file_name=%s""", (fname, fname))

def delete_file(fid, verbose=0):
	"""delete file from file system"""
	import os
	webnotes.conn.sql("delete from `tabFile Data` where name=%s", fid)	
	path = os.path.join(get_files_path(), fid.replace('/','-'))
	if os.path.exists(path):
		os.remove(path)
		
def get_file(fname):
	f = get_file_system_name(fname)
	if f:
		file_id = f[0][0].replace('/','-')
		file_name = f[0][1]
	else:
		file_id = fname
		file_name = fname

	# read the file
	import os
	with open(os.path.join(get_files_path(), file_id), 'r') as f:
		content = f.read()

	return [file_name, content]

files_path = None
def get_files_path():
	global files_path
	if not files_path:
		import os, conf
		files_path = os.path.join(os.path.dirname(os.path.abspath(conf.__file__)),
			'public', 'files')
	return files_path
