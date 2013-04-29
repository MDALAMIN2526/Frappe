// Copyright 2013 Web Notes Technologies Pvt Ltd
// License: MIT. See license.txt

// parent, args, callback
wn.upload = {
	make: function(opts) {
		var $upload = $("<div class='file-upload'>" + repl(wn._('Upload a file')+':<br>\
			<input type="file" name="filedata" /><br><br>\
			OR:<br><input type="text" name="file_url" /><br>\
			<p class="help">'
			+ (opts.sample_url || 'e.g. http://example.com/somefile.png') 
			+ '</p><br>\
			<input type="submit" class="btn btn-info btn-upload" value="'
				+wn._('Attach')+'" /></div>', {
				action: wn.request.url
			})).appendTo(opts.parent);
	

		// get the first file
		$upload.find(".btn-upload").click(function() {
			// convert functions to values
			for(key in opts.args) {
				if(typeof val==="function")
					opt.args[key] = opts.args[key]();
			}
			
			// add other inputs in the div as arguments
			$upload.find("input[name]").each(function() {
				var key = $(this).attr("name");
				if(key!="filedata" && key!="file_url") {
					opts.args[key] = $(this).val();
				}
			})
			
			opts.args.file_url = $upload.find('[name="file_url"]').val();

			var fileobj = $upload.find(":file").get(0).files[0];
			wn.upload.upload_file(fileobj, opts.args, opts.callback);
		})
	},
	upload_file: function(fileobj, args, callback) {
		if(!fileobj && !args.file_url) {
			msgprint(_("Please attach a file or set a URL"));
			return;
		}
		
		var _upload_file = function() {
			var msgbox = msgprint(wn._("Uploading..."));
			wn.call({
				"method": "uploadfile",
				args: args,
				callback: function(r) {
					msgbox.hide();
					if(r.exc) {
						msgprint("There were errors in uploading.");
					}
					callback(r.message, args.filename || args.file_url, r);
				}
			});
		}
		
		if(args.file_url) {
			_upload_file();
		} else {
			var freader = new FileReader();

			freader.onload = function() {
				args.filename = fileobj.name;
				args.filedata = freader.result.split(",")[1];
				_upload_file();
			};
			
			freader.readAsDataURL(fileobj);
		}
	}
}