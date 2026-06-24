
function loadModuleTable(
  table,
  url,
  errmsg,
  afterSuccess = null,
  always = null,
  btn = false
) {
  $.get(url, null, null, 'json')
    .done(function (data) {
      table.clear()
      $.each(data, function (k, v) {
        table.row.add(v)
      })
      table.draw()
      if (afterSuccess) afterSuccess(data)
      $("#btn_filter").html('Buscar');
      $("#btn_filter").attr('disabled', false);
    })
    .fail(function (x, t, e) {

      x.loto_error = {
        title: errmsg.title,
        detail: x.responseJSON.message
      };
    })
    .always(function () {
      if (always) always(data)
      if (btn) {
        $("#" + btn).html('Buscar');
        $("#" + btn).attr('disabled', false);
      }
    })
}

function fillForm(form, data) {
  $.each(data, function (k, v) {
    n = `[name='${k}']`;
    if (k.indexOf('[]') > 0) { //its a select multiple
      el = form.find(n);
      $.each(v, function (kk, vv) {
        el.find("option[value='" + vv + "']").prop("selected", true);
      })
    } else {
      el = form.find(n);
      if (el) el.val(v);
    }

  });
  return new Promise(function (resolve, reject) {
    resolve(data);
    //reject();
  });
}

function fillForm2(form, data) {
  $.each(data, function (k, v) {
    $.each(v, function (a, b) {
      o = `[name='${a}']`;
      al = form.find(o);
      if (al) al.val(b);
    });
  });
  return new Promise(function (resolve, reject) {
    resolve(data);
    //reject();
  });
}

function clearModalFormErrors(modal) {
  /**
   * @see https://formvalidation.io/guide/examples/hiding-success-class/
   * Note that resetForm didn't worked here
   */
  $f = modal.find('form')[0]
  $($f).trigger('reset')
  let groupEle = modal.find('.form-group')
  $.each(groupEle, function (k, v) {
    $(v)
      .removeClass(['has-success', 'has-danger'])
      .find('.is-valid, .is-invalid')
      .removeClass(['is-valid', 'is-invalid'])
    $(v)
      .find('.fv-plugins-message-container')
      .empty()
  })
}

function getFixedDatesFromRange(text_range) {
  let a = text_range.split(' - ')
  a[0] = a[0].replaceAll('/', '')
  a[1] = a[1].replaceAll('/', '')
  return a
}

const notBlankSpaceValidator = function () {
  return {
    validate: function (input) {
      if (input.value.search(/\s/) >= 0) {
        return {
          valid: false,
          message: 'Blank space not allowed'
        }
      }

      return {
        valid: true
      }
    }
  }
}

FormValidation.validators.notBlankSpace = notBlankSpaceValidator;

const numberLiteralValidator = function () {
  return {
    validate: function (input) {
      return {
        valid: /^\d+$/.test(input.value),
      }

    }
  }
}

FormValidation.validators.numberLiteral = numberLiteralValidator;

function getErrorFromJnResponse(x) {
  return (x && x.responseJSON !== undefined && x.responseJSON.message !== undefined) ?
    x.responseJSON.message : 'error';
}

function activateMenuItem(menuItem) {
  $mi = $(`[data-menuitem='${menuItem}']`);
  $mi.addClass('menu-item-active');
  $mi.parents('.menu-item.menu-item-submenu')
    .addClass('menu-item-open menu-item-here');
  $("#kt_aside_menu").scrollTop($mi.position().top);
}

function requestServer(path, data, callbacks, expecting = 'json') {
  //url = ajax_default_path + '/' + path;
  url = path;
  data = (data) ? data : {};
  exp = expecting === 'json' ? 'json' : 'default';
  taf = false;

  if (dataIsFormData(data)) {
    // check if there are any files inside
    for (var value of data.values()) {
      taf = (taf || (value instanceof File));
      if (taf) break;
    }
    if (data instanceof FormData) {
      taf = true;
    }
  }

  options = {
    type: 'POST',
    url: url,
    data: data,
    dataType: exp,
    timeout: 60000
  };
  if (taf) {
    options.processData = false;
    options.contentType = false;
  };

  $.post(options)
    .done(function (d) {
      if (callbacks && callbacks.hasOwnProperty('success')) {
        callbacks.success(d);
      }
    })
    .fail(function (x, ts) {
      if (x.status >= 500 && x.status <= 599) {
        response = `(${x.status}) ${x.statusText}`;
      } else if (ts == 'timeout') {
        showFail('Time for transaction is over.<br/>Please try again');
        response = '';
      } else {
        response = x.responseJSON;
      }
      (callbacks && callbacks.hasOwnProperty('fail')) ? callbacks.fail(response, x) : false;
    })
    .always(function () {
      (callbacks && callbacks.hasOwnProperty('always')) ? callbacks.always() : false;
    });
}

function dataIsFormData(data) {
  return (data instanceof FormData);
}

function removeItemFromSerializedData(data, item_name) {
  let r = [];
  r = data.filter(ar => { return (ar.name != item_name) });
  return r;
}

function converttime(input) {
  return moment(input, 'HH:mm:ss').format('h:mm A');
}

function convertdatetime(input) {
  return moment(input, 'YYYY-MM-DD HH:mm:ss').format('YYYY-MM-DD h:mm A');
}

/**
 * @see https://stackoverflow.com/a/1026087
 * @returns String
 */
function capitalizeText(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/* Bottom menu */

// resources in description
const mainTabs = document.querySelector(".main-tabs");
const mainSliderCircle = document.querySelector(".main-slider-circle");
const roundButtons = document.querySelectorAll(".round-button");

const colors = {
  blue: {
    50: {
      value: "#ffe0b2"
    },
    100: {
      value: "#ffe0b2"
    }
  },
  green: {
    50: {
      value: "#ffe0b2"
    },
    100: {
      value: "#ffe0b2"
    }
  },
  purple: {
    50: {
      value: "#ffe0b2"
    },
    100: {
      value: "#ffe0b2"
    }
  },
  orange: {
    50: {
      value: "#ffe0b2"
    },
    100: {
      value: "#ffe0b2"
    }
  },
  red: {
    50: {
      value: "#ffe0b2"
    },
    100: {
      value: "#ffe0b2"
    }
  }
};

const getColor = (color, variant) => {
  return colors[color][variant].value;
};

const handleActiveTab = (tabs, event, className) => {
  tabs.forEach((tab) => {
    tab.classList.remove(className);
  });

  if (!event.target.classList.contains(className)) {
    event.target.classList.add(className);
  }
};

("use strict");

const body = document.body;
const bgColorsBody = ["#fff", "#fff", "#fff", "#fff", "#fff"];
const menu = body.querySelector(".bottom-menu");
const menuItems = menu.querySelectorAll(".menu__item");
const menuBorder = menu.querySelector(".menu__border");
let activeItem = menu.querySelector(".active");

function clickItem(item, index) {
  menu.style.removeProperty("--timeOut");

  if (activeItem == item) return;

  if (activeItem) {
    activeItem.classList.remove("active");
  }

  item.classList.add("active");
  body.style.backgroundColor = bgColorsBody[index];
  activeItem = item;
  offsetMenuBorder(activeItem, menuBorder);
}

function offsetMenuBorder(element, menuBorder) {
  if (element) {
    const offsetActiveItem = element.getBoundingClientRect();
    const left =
      Math.floor(
        offsetActiveItem.left -
        menu.offsetLeft -
        (menuBorder.offsetWidth - offsetActiveItem.width) / 2
      ) + "px";
    menuBorder.style.transform = `translate3d(${left}, 0 , 0)`;
  }
}

offsetMenuBorder(activeItem, menuBorder);

menuItems.forEach((item, index) => {
  item.addEventListener("click", () => clickItem(item, index));
});

window.addEventListener("resize", () => {
  offsetMenuBorder(activeItem, menuBorder);
  menu.style.setProperty("--timeOut", "none");
});

function getCookieVal(offset) {
  var endstr = document.cookie.indexOf(";", offset);
  if (endstr == -1)
    endstr = document.cookie.length;
  return unescape(document.cookie.substring(offset, endstr));
}

function GetCookie(name) {
  var arg = name + "=";
  var alen = arg.length;
  var clen = document.cookie.length;
  var i = 0;
  while (i < clen) {
    var j = i + alen;
    if (document.cookie.substring(i, j) == arg)
      return getCookieVal(j);
    i = document.cookie.indexOf(" ", i) + 1;
    if (i == 0) break;
  }
  return null;
}

function SetCookie(name, value) {
  var argv = SetCookie.arguments;
  var argc = SetCookie.arguments.length;
  var expires = (argc > 2) ? argv[2] : null;
  var path = (argc > 3) ? argv[3] : null;
  var domain = (argc > 4) ? argv[4] : null;
  var secure = (argc > 5) ? argv[5] : false;
  document.cookie = name + "=" + escape(value) +
    ((expires == null) ? "" : ("; expires=" + expires.toGMTString())) +
    ((path == null) ? "" : ("; path=" + path)) +
    ((domain == null) ? "" : ("; domain=" + domain)) +
    ((secure == true) ? "; secure" : "");
}

function DeleteCookie(name) {
  var exp = new Date();
  exp.setTime(exp.getTime() - 1); // This cookie is history
  var cval = GetCookie(name);
  document.cookie = name + "=; expires=" + exp.toGMTString();
}
/* Bottom menu end */