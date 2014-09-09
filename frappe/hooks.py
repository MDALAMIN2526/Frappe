app_name = "frappe"
app_title = "Frappe Framework"
app_publisher = "Web Notes Technologies Pvt. Ltd."
app_description = "Full Stack Web Application Framwork in Python"
app_icon = "assets/frappe/images/frappe.svg"
app_version = "4.3.0"
app_color = "#3498db"
app_email = "support@frappe.io"

before_install = "frappe.utils.install.before_install"
after_install = "frappe.utils.install.after_install"

# website
app_include_js = "assets/js/frappe.min.js"
app_include_css = [
		"assets/frappe/css/splash.css",
		"assets/css/frappe.css"
	]
web_include_js = [
		"assets/js/frappe-web.min.js",
		"website_script.js"
	]
web_include_css = [
		"assets/css/frappe-web.css",
		"style_settings.css"
	]

website_clear_cache = "frappe.website.doctype.website_group.website_group.clear_cache"

write_file_keys = ["file_url", "file_name"]

notification_config = "frappe.core.notifications.get_notification_config"

before_tests = "frappe.utils.install.before_tests"

website_generators = ["Web Page", "Blog Post", "Website Group", "Blog Category", "Web Form"]

# login

on_session_creation = "frappe.desk.doctype.feed.feed.login_feed"

# permissions

permission_query_conditions = {
	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
	"ToDo": "frappe.desk.doctype.todo.todo.get_permission_query_conditions",
	"User": "frappe.core.doctype.user.user.get_permission_query_conditions",
	"Feed": "frappe.desk.doctype.feed.feed.get_permission_query_conditions"
}

has_permission = {
	"Event": "frappe.desk.doctype.event.event.has_permission",
	"ToDo": "frappe.desk.doctype.todo.todo.has_permission",
	"User": "frappe.core.doctype.user.user.has_permission",
	"Feed": "frappe.desk.doctype.feed.feed.has_permission"
}

doc_events = {
	"*": {
		"after_insert": "frappe.email.doctype.email_alert.email_alert.trigger_email_alerts",
		"validate": "frappe.email.doctype.email_alert.email_alert.trigger_email_alerts",
		"on_update": [
			"frappe.core.doctype.notification_count.notification_count.clear_doctype_notifications",
			"frappe.email.doctype.email_alert.email_alert.trigger_email_alerts",
			"frappe.desk.doctype.feed.feed.update_feed"
		],
		"after_rename": "frappe.core.doctype.notification_count.notification_count.clear_doctype_notifications",
		"on_submit": [
			"frappe.email.doctype.email_alert.email_alert.trigger_email_alerts",
			"frappe.desk.doctype.feed.feed.update_feed"
		],
		"on_cancel": [
			"frappe.core.doctype.notification_count.notification_count.clear_doctype_notifications",
			"frappe.email.doctype.email_alert.email_alert.trigger_email_alerts"
		],
		"on_trash": "frappe.core.doctype.notification_count.notification_count.clear_doctype_notifications"
	},
	"Website Route Permission": {
		"on_update": "frappe.website.doctype.website_group.website_group.clear_cache_on_doc_event"
	}
}

scheduler_events = {
	"all": ["frappe.email.bulk.flush"],
	"daily": [
		"frappe.email.bulk.clear_outbox",
		"frappe.core.doctype.notification_count.notification_count.clear_notifications",
		"frappe.desk.doctype.event.event.send_event_digest",
		"frappe.sessions.clear_expired_sessions",
		"frappe.email.doctype.email_alert.email_alert.trigger_daily_alerts",
	],
	"hourly": [
		"frappe.website.doctype.website_group.website_group.clear_event_cache"
	]
}

mail_footer = "frappe.email.doctype.outgoing_email_settings.outgoing_email_settings.get_mail_footer"
