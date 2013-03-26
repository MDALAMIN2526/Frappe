// Copyright 2013 Web Notes Technologies Pvt Ltd
// License: MIT. See license.txt

// parent, args, callback
wn.upload = {
	make: function(opts) {
		var id = wn.dom.set_unique_id();
		$(opts.parent).append(repl('<iframe id="%(id)s" name="%(id)s" src="blank.html" \
				style="width:0px; height:0px; border:0px"></iframe>\
			<form method="POST" enctype="multipart/form-data" \
				action="%(action)s" target="%(id)s">\
				'+wn._('Upload a file')+':<br>\
				<input type="file" name="filedata" /><br><br>\
				OR:<br><input type="text" name="file_url" /><br>\
				<p class="help">'
				+ (opts.sample_url || 'e.g. http://example.com/somefile.png') 
				+ '</p><br>\
				<input type="submit" class="btn" value="'+wn._('Attach')+'" />\
			</form>', {
				id: id,
				action: wn.request.url
			}));
	
		opts.args.cmd = 'uploadfile';
		opts.args._id = id;
			
		// add request parameters
		for(key in opts.args) {
			if(opts.args[key]) {
				if(typeof val==="function") {
					var val = opts.args[key]();
				} else {
					var val = opts.args[key];
				}
				$('<input type="hidden">')
					.attr('name', key)
					.attr('value', val)
					.appendTo($(opts.parent).find('form'));
			}
		}
		
		$('#' + id).get(0).callback = opts.callback
		
	},
	callback: function(id, file_id, args) {
		$('#' + id).get(0).callback(file_id, args);
	}
}