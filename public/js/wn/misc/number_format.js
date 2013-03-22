// Copyright 2013 Web Notes Technologies Pvt Ltd
// MIT Licensed. See license.txt

wn.number_format_info = {
	"#,###.##": {decimal_str:".", group_sep:",", precision:2},
	"#.###,##": {decimal_str:",", group_sep:".", precision:2},
	"# ###.##": {decimal_str:".", group_sep:" ", precision:2},
	"#,###.###": {decimal_str:".", group_sep:",", precision:3},
	"#,##,###.##": {decimal_str:".", group_sep:",", precision:2},
	"#.###": {decimal_str:"", group_sep:".", precision:0},
	"#,###": {decimal_str:"", group_sep:",", precision:0},
}

window.format_number = function(v, format, decimals){ 
	if (!format) {
		format = get_number_format();
	}
	info = get_number_format_info(format);
	
	//Fix the decimal first, toFixed will auto fill trailing zero.
	decimals = decimals || info.precision;
	
	v = flt(v, decimals, format);

	if(v<0) var is_negative = true; 
	v = Math.abs(v);
	
	v = v.toFixed(decimals);

	var part = v.split('.');
	
	// get group position and parts
	var group_position = info.group_sep ? 3 : 0;

	if (group_position) {
		var integer = part[0];
		var str = '';
		var offset = integer.length % group_position;
		for (var i=integer.length; i>=0; i--) { 
			var l = replace_all(str, info.group_sep, "").length;
			if(format=="#,##,###.##" && str.indexOf(",")!=-1) { // INR
				group_position = 2;
				l += 1;
			}
			
			str += integer.charAt(i); 

			if (l && !((l+1) % group_position) && i!=0 ) {
				str += info.group_sep;
			}
		}
		part[0] = str.split("").reverse().join("");
	}
	if(part[0]+""=="") {
		part[0]="0";
	}
	
	// join decimal
	part[1] = part[1] ? (info.decimal_str + part[1]) : "";
	
	// join
	return (is_negative ? "-" : "") + part[0] + part[1];
};

function format_currency(v, currency) {
	var format = get_number_format(currency);
		
	var symbol = get_currency_symbol(currency);

	if(symbol)
		return symbol + " " + format_number(v, format);
	else
		return format_number(v, format);
}

function get_currency_symbol(currency) {
	if(wn.boot.sysdefaults.hide_currency_symbol=="Yes")
		return null;

	if(!currency)
		currency = wn.boot.sysdefaults.currency;

	return wn.model.get_value("Currency", currency, "symbol") || currency;
}

var global_number_format = null;
function get_number_format(currency) {
	if(!global_number_format) {
		global_number_format = wn.boot.sysdefaults.number_format
			|| wn.model.get_value("Currency", wn.boot.sysdefaults.currency, "number_format")
			|| "#,###.##";
	}
	
	var number_format;
	if(currency) {
		number_format = wn.model.get_value("Currency", currency, 
			"number_format");
	}
	
	return number_format || global_number_format;
}

function get_number_format_info(format) {
	var info = wn.number_format_info[format];
	if(!info) {
		info = {decimal_str:".", group_sep:",", precision:2};
	}
	return info;
}