function getData(resourceName, data={}, params={}, callback=null){
    call('GET', resourceName, data, params, callback)
}

function postData(resourceName, data={}, params={}, callback=null){
    call('POST', resourceName, data, params, callback)
}

function putData(resourceName, data={}, params={}, callback=null){
    call('PUT', resourceName, data, params, callback)
}

function call(method, urlExt, sendData={}, params={}, callback=null){
    urlExt = urlExt.toLowerCase();
    if(urlExt.charAt(urlExt.length-1) != '/') urlExt += '/';
    urlExt += '?' + new URLSearchParams(params).toString();
    var request_data = {method: method, headers: {'Content-Type':'application/json','X-CSRFToken': token}};
    if(method != 'GET') request_data['body'] = JSON.stringify(sendData);
    fetch('api' + urlExt, request_data).then(response => response.json()).then(result => {if(callback != null) callback(result)});
}

function flash(element){
    var rgb = window.getComputedStyle(element).backgroundColor;
    rgb = rgb.substring(4, rgb.length-1).replace(/ /g, '').split(',');
    var r = rgb[0], g = rgb[1], bOrigin = rgb[2], b = bOrigin;
    var add = false;
    var complete = false;
    const increment = 15;
    var flashOn = setInterval(() => {
        if(add){
            if(b < 255 && (b+increment) <= 255){
                b += increment;
            }else{
                add = false;
                complete = true;
            }
        }else{
            if(complete == true && b < bOrigin){
                b = bOrigin;
                clearInterval(flashOn);
            }
            else if(b > 0 && (b-increment) >= 0){
                b -= increment;
            }else{
                add = true;
            }
        }
        element.style.backgroundColor = 'RGB('+r+','+g+','+b+')';
        if(b == bOrigin) element.style.removeProperty("background-color");
    }, 50);
}