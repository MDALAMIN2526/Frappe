// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

frappe.standard_pages["test-runner"] = function() {
	var wrapper = frappe.container.add_page('test-runner');

	frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true,
		title: frappe._("Test Runner")
	});
	
	$("<div id='qunit'></div>").appendTo($(wrapper).find(".layout-main"));

	var route = frappe.get_route();
	if(route.length < 2) {
		msgprint("To run a test add the module name in the route after 'test-runner/'. \
			For example, #test-runner/lib/js/frappe.test_app.js");
		return;
	}

	frappe.require("assets/frappe/js/lib/jquery/qunit.js");
	frappe.require("assets/frappe/js/lib/jquery/qunit.css");
	
	QUnit.load();

	frappe.require(route.splice(1).join("/"));
}