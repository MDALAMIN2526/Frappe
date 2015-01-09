// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

// __("Form")

// parent, title, single_column
// standard page with page

frappe.ui.make_app_page = function(opts) {
	/* help: make a standard page layout with a toolbar and title */
	/* options: [
			"parent: [HTMLElement] parent element",
			"single_column: [Boolean] false/true",
			"title: [optional] set this title"
		]
	*/

	opts.parent.page = new frappe.ui.Page(opts);
	return opts.parent.page;
}

frappe.ui.Page = Class.extend({
	init: function(opts) {
		$.extend(this, opts);

		this.set_document_title = true;
		this.buttons = {};
		this.fields_dict = {};
		this.views = {};

		this.make();

	},

	make: function() {
		this.wrapper = $(this.parent);

		$(frappe.render_template("page", {})).appendTo(this.wrapper);

		if(this.single_column) {
			this.add_view("main", '<div class="layout-main layout-main-section">');
		} else {
			var main = this.add_view("main", '<div class="row layout-main">\
				<div class="col-sm-2 layout-side-section"></div>\
				<div class="col-sm-10">\
					<div class="layout-main-section"></div>\
				</div>\
			</div>');
		}

		this.$title_area = this.wrapper.find("h1");

		this.$sub_title_area = this.wrapper.find("h6");

		if(this.set_document_title!==undefined)
			this.set_document_title = this.set_document_title;

		if(this.title)
			this.set_title(this.title);

		if(this.icon)
			this.get_main_icon(this.icon);

		this.main = this.wrapper.find(".layout-main-section");
		this.sidebar = this.wrapper.find(".layout-side-section");
		this.indicator = this.wrapper.find(".indicator");

		this.page_actions = this.wrapper.find(".page-actions");

		this.btn_primary = this.page_actions.find(".primary-action");
		this.btn_secondary = this.page_actions.find(".btn-secondary");

		this.menu = this.page_actions.find(".menu-btn-group .dropdown-menu");
		this.menu_btn_group = this.page_actions.find(".menu-btn-group");

		this.actions = this.page_actions.find(".actions-btn-group .dropdown-menu");
		this.actions_btn_group = this.page_actions.find(".actions-btn-group");

		this.page_form = $('<div class="page-form row hide"></div>').prependTo(this.main);
		this.icon_group = this.page_actions.find(".page-icon-group");
	},

	set_indicator: function(label, color) {
		this.clear_indicator().removeClass("hide").html(label).addClass(color);
	},

	add_action_icon: function(icon, click) {
		return $('<a class="text-extra-muted"><i class="'+icon+'"></i></a>')
			.appendTo(this.icon_group.removeClass("hide"))
			.click(click);
	},

	clear_indicator: function() {
		return this.indicator.removeClass().addClass("indicator hide");
	},

	set_primary_action: function(label, click) {
		this.btn_primary.removeClass("hide").prop("disabled", false).html(label).on("click", click);
	},

	set_secondary_action: function(label, click) {
		this.btn_secondary.removeClass("hide").prop("disabled", false).html(label).on("click", click);
	},

	clear_primary_action: function() {
		this.btn_primary.addClass("hide");
	},

	clear_actions: function() {
		this.btn_primary.addClass("hide").unbind("click");
		this.btn_secondary.addClass("hide").unbind("click");
	},

	clear_icons: function() {
		this.icon_group.addClass("hide").empty();
	},

	//--- Menu --//

	add_menu_item: function(label, click, standard) {
		return this.add_dropdown_item(label, click, standard, this.menu);
	},

	clear_menu: function() {
		this.clear_btn_group(this.menu);
	},

	show_menu: function() {
		this.menu_btn_group.removeClass("hide");
	},

	hide_menu: function() {
		this.menu_btn_group.addClass("hide");
	},

	//--- Actions (workflow) --//

	add_action_item: function(label, click, standard) {
		return this.add_dropdown_item(label, click, standard, this.actions);
	},

	clear_actions_menu: function() {
		this.clear_btn_group(this.actions);
	},

	//-- Generic --//

	add_dropdown_item: function(label, click, standard, parent) {
		parent.parent().removeClass("hide");

		var $li = $('<li><a class="grey-link">'+ label +'</a><li>'),
			$link = $li.find("a").on("click", click);

		if(standard===true) {
			$li.appendTo(parent);
		} else {
			this.divider = parent.find(".divider");
			if(!this.divider.length) {
				this.divider = $('<li class="divider user-action"></li>').prependTo(parent);
			}
			$li.addClass("user-action").insertBefore(this.divider);
		}

		return $link;
	},

	clear_btn_group: function(parent) {
		parent.empty();
		parent.parent().addClass("hide");
	},

	add_divider: function() {
		return $('<li class="divider"></li>').appendTo(this.menu);
	},

	//---//

	clear_user_actions: function() {
		this.menu.find(".user-action").remove();
	},

	// page::title
	get_title_area: function() {
		return this.$title_area;
	},

	set_title: function(txt, icon) {
		// strip icon
		this.title = txt;
		document.title = txt.replace(/<[^>]*>/g, "");
		if(icon) {
			txt = '<span class="'+ icon +' text-muted" style="font-size: 24px;"></span> ' + txt;
		}
		this.$title_area.find(".title-text").html(txt);
	},

	set_title_sub: function(txt) {
		// strip icon
		this.$sub_title_area.html(txt).toggleClass("hide", !!!txt);
	},

	add_module_icon: function(module, doctype, onclick, sub_title) {
		var module_info = frappe.get_module(module);
		if(!module_info) {
			module_info = {
				icon: "icon-question-sign",
				color: "#ddd"
			}
		}
		var icon = frappe.boot.doctype_icons[doctype] || module_info.icon;

		this.get_main_icon(icon)
			.attr("doctype-name", doctype);

		this.set_title_left(function() {
			var route = frappe.get_route()[0]==module_info.link ? "" : module_info.link;
			frappe.set_route(route);
		});
	},

	get_main_icon: function(icon) {
		return this.$title_area.find(".title-icon")
			.html('<i class="'+icon+' icon-fixed-width"></i> ')
			.toggle(true);
		},

	add_help_button: function(txt) {
		this.add_icon_btn("2", "icon-question-sign", __("Help"),
			function() { msgprint($(this).data('help-text'), 'Help'); })
			.data("help-text", txt);
	},

	add_icon_btn: function(group, icon, label, click) {
		return this.iconbar.add_btn(group, icon, label, click);
	},

	add_button: function(label, click, icon, is_title) {
		return this.add_icon_btn("1", icon, __(label), click);
	},

	add_dropdown_button: function(parent, label, click, icon) {
		frappe.ui.toolbar.add_dropdown_button(parent, label, click, icon);
	},

	// page::form
	add_label: function(label) {
		this.show_form();
		return $("<label class='col-md-1 page-only-label'>"+label+" </label>")
			.appendTo(this.page_form);
	},
	add_select: function(label, options) {
		var field = this.add_field({label:label, fieldtype:"Select"})
		return field.$wrapper.find("select").empty().add_options(options);
	},
	add_data: function(label) {
		var field = this.add_field({label: label, fieldtype: "Data"});
		return field.$wrapper.find("input").attr("placeholder", label);
	},
	add_date: function(label, date) {
		var field = this.add_field({label: label, fieldtype: "Date", "default": date});
		return field.$wrapper.find("input").attr("placeholder", label);
	},
	add_check: function(label) {
		return $("<div class='checkbox'><label><input type='checkbox'>" + label + "</label></div>")
			.appendTo(this.page_form)
			.find("input");
	},
	add_break: function() {
		// add further fields in the next line
		this.page_form.append('<div class="clearfix invisible-xs"></div>');
	},
	add_field: function(df) {
		this.show_form();
		var f = frappe.ui.form.make_control({
			df: df,
			parent: this.page_form,
			only_input: df.fieldtype=="Check" ? false : true,
		})
		f.refresh();
		$(f.wrapper)
			.addClass('col-md-2')
			.attr("title", __(df.label)).tooltip();
		f.$input.addClass("input-sm").attr("placeholder", __(df.label));

		if(df.fieldtype==="Check") {
			$(f.wrapper).find(":first-child")
				.removeClass("col-md-offset-4 col-md-8");
		}

		if(df.fieldtype=="Button") {
			$(f.wrapper).find(".page-control-label").html("&nbsp;")
			f.$input.addClass("btn-sm").css({"width": "100%", "margin-top": "-1px"});
		}

		if(df["default"])
			f.set_input(df["default"])
		this.fields_dict[df.fieldname || df.label] = f;
		return f;
	},
	show_form: function() {
		this.page_form.removeClass("hide");
	},
	add_view: function(name, html) {
		this.views[name] = $(html).appendTo($(this.wrapper).find(".page-content"));
		if(!this.current_view) {
			this.current_view = this.views[name];
		} else {
			this.views[name].toggle(false);
		}
		return this.views[name];
	},
	set_view: function(name) {
		this.current_view && this.current_view.toggle(false);
		this.current_view = this.views[name];

		this.previous_view_name = this.current_view_name;
		this.current_view_name = name;

		this.views[name].toggle(true);
	}
});
