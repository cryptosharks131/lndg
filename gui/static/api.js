async function GET(url, {method = 'GET', data} = {}){
    if(!data.limit) data.limit = 100000
    if(!data.format) data.format = 'json'
    return call({url, method, data})
}

async function POST(url, {method = 'POST', body}){
    return call({url, method, body})
}

async function PUT(url, {method = 'PUT', body}){
    return call({url, method, body})
}

async function PATCH(url, {method = 'PATCH', body}){
    return call({url, method, body})
}

async function DELETE(url, {method = 'DELETE'} = {}){
    return call({url, method})
}

async function call({url, method, data, body, headers = {'Content-Type':'application/json'}}){
    if(url.charAt(url.length-1) != '/') url += '/'
    if(method != 'GET') headers['X-CSRFToken'] = document.getElementById('api').dataset.token
    const result = await fetch(`/api/${url}${data ? '?': ''}${new URLSearchParams(data).toString()}`, {method, body: JSON.stringify(body), headers})
    return result.json()
}

class Sync{
    static PUT(url, {method = 'PUT', body}, callback){
        call({url, method, body}).then(res => callback(res))
    }
    static POST(url, {method = 'POST', body}, callback){
        call({url, method, body}).then(res => callback(res))
    }
}