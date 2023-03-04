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
    param_counter = 0;
    for (param in params){
        var parameter = params[param];
        if (param_counter > 0) urlExt += '&';
        urlExt += '?' + param + '=' + parameter;
        param_counter += 1;
    };
    const response = fetch('api' + urlExt, {
        method: method,
        headers: {'Content-Type':'application/json','X-CSRFToken': token},
        body: JSON.stringify(sendData),
    });
}