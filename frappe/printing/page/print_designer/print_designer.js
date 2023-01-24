frappe.pages["print-designer"].on_page_load = function (wrapper) {
	// hot reload in development
	if (frappe.boot.developer_mode) {
		frappe.hot_update = frappe.hot_update || [];
		frappe.hot_update.push(() => load_print_designer(wrapper));
	}
};

frappe.pages["print-designer"].on_page_show = function (wrapper) {
	load_print_designer(wrapper);
};

const load_print_designer = (wrapper) => {
	let route = frappe.get_route();
	let $parent = $(wrapper);
	if (wrapper.__vue_app__) return;

	if (route.length > 1) {
		frappe.require("print_designer.bundle.js").then(() => {
			frappe.print_designer = new frappe.ui.PrintDesigner({
				wrapper: $parent,
				page: wrapper.page,
				print_format: route[1],
			});
		});
	} else {
		let d = new frappe.ui.Dialog({
			title: __("Create or Edit Print Format"),
			fields: [
				{
					label: __("Action"),
					fieldname: "action",
					fieldtype: "Select",
					options: [
						{ label: __("Create New"), value: "Create" },
						{ label: __("Edit Existing"), value: "Edit" },
					],
					change() {
						let action = d.get_value("action");
						d.get_primary_btn().text(action === "Create" ? __("Create") : __("Edit"));
					},
				},
				{
					label: __("Select Document Type"),
					fieldname: "doctype",
					fieldtype: "Link",
					options: "DocType",
					filters: {
						istable: 0,
					},
					reqd: 1,
					default: frappe.route_options ? frappe.route_options.doctype : null,
				},
				{
					label: __("Print Format Name"),
					fieldname: "print_format_name",
					fieldtype: "Data",
					depends_on: (doc) => doc.action === "Create",
					mandatory_depends_on: (doc) => doc.action === "Create",
				},
				{
					label: __("Select Print Format"),
					fieldname: "print_format",
					fieldtype: "Link",
					options: "Print Format",
					only_select: 1,
					depends_on: (doc) => doc.action === "Edit",
					get_query() {
						return {
							filters: {
								doc_type: d.get_value("doctype"),
								print_designer: 1,
							},
						};
					},
					mandatory_depends_on: (doc) => doc.action === "Edit",
				},
			],
			primary_action_label: __("Edit"),
			primary_action({ action, doctype, print_format, print_format_name }) {
				if (action === "Edit") {
					frappe.set_route("print-designer", print_format);
				} else if (action === "Create") {
					d.get_primary_btn().prop("disabled", true);
					frappe.db
						.insert({
							doctype: "Print Format",
							name: print_format_name,
							doc_type: doctype,
							print_designer: 1,
						})
						.then((doc) => {
							frappe.set_route("print-designer", doc.name);
						})
						.finally(() => {
							d.get_primary_btn().prop("disabled", false);
						});
				}
			},
		});
		d.set_value("action", "Create");
		d.show();
	}
};
