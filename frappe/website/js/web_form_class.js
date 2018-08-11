export default class WebForm {
	constructor(options) {
		// wrapper, doctype, docname, web_form_name, allow_incomplete
		Object.assign(this, options);
		this.get_data();
	}

	get_data() {
		frappe.call({
			method: 'frappe.website.doctype.web_form.web_form.get_form_data',
			args: {
				doctype: this.doctype,
				docname: this.docname,
				web_form_name: this.web_form_name
			},
			freeze: true
		}).then(r => {
			const { doc, web_form, links } = r.message;
			this.render(doc, web_form, links);
		});
	}

	render(doc, web_form, links) {
		const query_params = frappe.utils.get_query_params();

		web_form.web_form_fields.map(df => {
			if (df.fieldtype === 'Table') {
				df.get_data = () => {
					let data = []
					if(doc) {
						data = doc[df.fieldname];
					}
					return data;
				}

				df.fields = [
					{
						fieldtype: 'Link',
						fieldname: "role",
						options: "Role",
						label: __("Role"),
						in_list_view: 1 // added
					}
				];

				df.options = null;
			}

			if (df.fieldtype==='Attach') {
				df.is_private = true;
			}

			// Set defaults
			if (query_params && query_params["new"] == 1 && df.fieldname in query_params) {
				df.default = query_params[df.fieldname];
			}

			delete df.parent;
			delete df.parentfield;
			delete df.parenttype;
			delete df.doctype;

			return df;
		});

		this.field_group = new frappe.ui.FieldGroup({
			parent: this.wrapper,
			fields: web_form.web_form_fields
		});

		this.field_group.make();

		this.wrapper.find(".form-column").unwrap(".section-body");

		if(doc) {
			this.field_group.set_values(doc);
		}
	}

	get_values() {
		let values = this.field_group.get_values(this.allow_incomplete);
		if (!values) return null;
		values.doctype = this.doctype;
		values.name = this.docname;
		values.web_form_name = this.web_form_name;
		return values;
	}

	get_field(fieldname) {
		const field = this.field_group.fields_dict[fieldname];
		if (!field) {
			throw `No field ${fieldname}`;
		}
		return field;
	}

	get_input(fieldname) {
		const $input = this.get_field(fieldname).$input;
		if (!$input) {
			throw `Cannot set trigger for ${fieldname}`;
		}
		return $input;
	}

	get_value(fieldname) {
		return this.fieldname.get_value(fieldname);
	}

	set_value(fieldname, value) {
		return this.field_group.set_value(fieldname, value);
	}

	set_field_property(fieldname, property, value) {
		const field = this.get_field(fieldname);
		field.df[property] = value;
		field.refresh();
	}

	on(fieldname, fn) {
		const field = this.get_field(fieldname);
		const $input = this.get_input(fieldname);
		$input.on('change', (event) => {
			return fn(field, field.get_value(), event);
		});
	}

	validate() {
		return true;
	}
}
