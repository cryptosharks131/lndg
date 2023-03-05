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