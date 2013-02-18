// Copyright 2013 Web Notes Technologies Pvt Ltd
// License: MIT. See license.txt

wn.provide('wn.views.formview');

wn.views.formview = {
	show: function(dt, dn) {
		// renamed (on save)?
		if(wn.model.new_names[dn])
			dn = wn.model.new_names[dn];
		wn.views.formview.make(dt, dn, true);
	},
	make: function(dt, dn, show) {
		// show doctype
		wn.model.with_doctype(dt, function() {
			wn.model.with_doc(dt, dn, function(dn, r) {
				if(r && r['403']) return; // not permitted
				
				if(!(locals[dt] && locals[dt][dn])) {
					// doc not found, but starts with New,
					// make a new doc and set it
					if(dn && dn.substr(0,4)=="New ") {
						var new_name = wn.model.make_new_doc_and_get_name(dt);
						wn.views.formview.show(dt, new_name);
						return;
					} else {
						wn.set_route('404');
					}
					return;
				}
				if(!wn.views.formview[dt]) {
					wn.views.formview[dt] = wn.container.add_page('Form - ' + dt);
					wn.views.formview[dt].frm = new _f.Frm(dt, wn.views.formview[dt], true);
				}
				
				if(show) {
					wn.container.change_to('Form - ' + dt);
					wn.views.formview[dt].frm.refresh(dn);
				}
			});
		});
	},
	create: function(dt) {
		var new_name = wn.model.make_new_doc_and_get_name(dt);
		wn.set_route('Form', dt, new_name);
	}
}
