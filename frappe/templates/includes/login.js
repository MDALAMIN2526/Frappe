var disable_signup = {{ disable_signup and "true" or "false" }};
var login = {};

$(window).on("hashchange", function() {
	var route = window.location.hash.slice(1);
	if(!route) route = "login";
	login[route]();
})

// Login
login.do_login = function(){
	var args = {};
	if(window.is_sign_up) {
		args.cmd = "frappe.core.doctype.profile.profile.sign_up";
		args.email = ($("#login_id").val() || "").trim();
		args.full_name = ($("#full_name").val() || "").trim();

		if(!args.email || !valid_email(args.email) || !args.full_name) {
			login.set_message("Valid email and name required.");
			return false;
		}
	} else if(window.is_forgot) {
		args.cmd = "frappe.core.doctype.profile.profile.reset_password";
		args.user = ($("#login_id").val() || "").trim();
		
		if(!args.user) {
			login.set_message("Valid Login Id required.");
			return false;
		}

	} else {
		args.cmd = "login"
		args.usr = ($("#login_id").val() || "").trim();
		args.pwd = $("#pass").val();

		if(!args.usr || !args.pwd) {
			login.set_message("Both login and password required.");
			return false;
		}	
	}

	$('#login_btn').prop("disabled", true);
	$("#login-spinner").toggle(true);
	$('#login_message').toggle(false);
		
	$.ajax({
		type: "POST",
		url: "/",
		data: args,
		dataType: "json",
		statusCode: login.login_handlers
	}).always(function(){
		$("#login-spinner").toggle(false);
		$('#login_btn').prop("disabled", false);
	})
	
	return false;
}

login.set_heading = function(html) {
	$(".panel-heading").html("<h4>" + html + "</h4>");
}

login.login = function() {
	login.set_heading('<i class="icon-lock"></i> Login');
	$("#login_wrapper h3").html("Login");
	$("#login_id").attr("placeholder", "Login Email Id");
	$("#password-row").toggle(true);
	$("#full-name-row, #login_message").toggle(false);
	$("#login_btn").html("Login").removeClass("btn-success");
	$("#forgot-link").html('<a href="#forgot">Forgot Password?</a>');
	
	if(!disable_signup) {
		$("#switch-view").empty().append('<div>\
			No Account? <a class="btn btn-success" style="margin-left: 10px; margin-top: -2px;"\
				href="#sign_up">Sign Up</button></div>');
	}

	window.is_login = true;
	window.is_sign_up = false;
	window.is_forgot = false;
}

login.sign_up = function() {
	login.set_heading('<i class="icon-thumbs-up"></i> Sign Up');
	$("#login_id").attr("placeholder", "Your Email Id");
	$("#password-row, #login_message").toggle(false);
	$("#full-name-row").toggle(true);
	$("#login_btn").html("Sign Up").addClass("btn-success");
	$("#forgot-link").html("<a href='#login'>Login</a>");
	$("#switch-view").empty();
	window.is_sign_up = true;
}

login.forgot = function() {
	login.set_heading('<i class="icon-question-sign"></i> Forgot');
	$("#login_id").attr("placeholder", "Your Email Id");
	$("#password-row, #login_message, #full-name-row").toggle(false);
	$("#login_btn").html("Send Password").removeClass("btn-success");
	$("#forgot-link").html("<a href='#login'>Login</a>");
	$("#switch-view").empty();
	window.is_forgot = true;
	window.is_sign_up = false;
}

login.set_message = function(message, color) {
	frappe.msgprint(message);
	return;
	//$('#login_message').html(message).toggle(true);	
}

login.login_handlers = {
	200: function(data) {
		if(data.message=="Logged In") {
			window.location.href = "app";
		} else if(data.message=="No App") {
			if(localStorage) {
				var last_visited = localStorage.getItem("last_visited") || "/index";
				localStorage.removeItem("last_visited");
				window.location.href = last_visited;
			} else {
				window.location.href = "/index";
			}
		} else if(window.is_sign_up) {
			frappe.msgprint(data.message);
		}			
	},
	401: function(xhr, data) {
		login.set_message("Invalid Login");
	}
}


{% if fb_app_id is defined -%}
// facebook login
$(document).ready(function() {
  var user_id = frappe.get_cookie("user_id");
  var sid = frappe.get_cookie("sid");
  
  // logged in?
  if(!sid || sid==="Guest") {
	  // fallback on facebook login -- no login again
	  $(".btn-login").html("Login via Facebook").removeAttr("disabled");
  } else {
	  // get private stuff (if access)
	  // app.setup_user({"user": user_id});
  }
  
});

$(function() {
	$login = $(".btn-login").prop("disabled", true);
	$.getScript('//connect.facebook.net/en_UK/all.js', function() {
		$login.prop("disabled", false);
		FB.init({
		  appId: '{{ fb_app_id }}',
		}); 
		$login.click(function() {
			$login.prop("disabled", true).html("Logging In...");
			login.via_facebook();
		});
	});
});

login.via_facebook = function() {
	// not logged in to facebook either
	FB.login(function(response) {
	   if (response.authResponse) {
		   // yes logged in via facebook
		   console.log('Welcome!  Fetching your information.... ');
		   var fb_access_token = response.authResponse.accessToken;

		   // get user graph
		   FB.api('/me', function(response) {
			   response.fb_access_token = fb_access_token || "[none]";
			   $.ajax({
					url:"/",
					type: "POST",
					data: {
						cmd:"frappe.core.doctype.profile.profile.facebook_login",
						data: JSON.stringify(response)
					},
					statusCode: login.login_handlers
				})
			});
		} else {
			frappe.msgprint("You have denied access to this application via Facebook. \
				Please change your privacy settings in Facebook and try again. \
				If you do not want to use Facebook login, <a href='/login'>sign-up</a> here");
		}
	},{scope:"email"});	
}
{%- endif %}

$(document).ready(function(wrapper) {
	window.location.hash = "#login";
	login.login();
	
	$('#login_btn').click(login.do_login);
		
	$('#pass').keypress(function(ev){
		if(ev.which==13 && $('#pass').val()) {
			$("#login_btn").click();
		}
	});
	$(document).trigger('login_rendered');
})