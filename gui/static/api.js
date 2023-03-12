async function GET(url, {method = 'GET', data = null}){
    return call({url, method, data})
}

async function POST(url, {method = 'POST', body}){
    return call({url: url + '/', method, body})
}

async function PUT(url, {method = 'PUT', body}){
    return call({url: url + '/', method, body})
}

async function PATCH(url, {method = 'PATCH', body}){
    return call({url: url + '/', method, body})
}

async function DELETE(url, {method = 'DELETE'}){
    return call({url: url + '/', method})
}

async function call({url, method, data, body, headers = {'Content-Type':'application/json'}}){
    if(method != 'GET') headers['X-CSRFToken'] = token
    const result = await fetch(`api/${url}${data ? '?': ''}${new URLSearchParams(data).toString()}`, {method, body: JSON.stringify(body), headers})
    return result.json()
}

class Sync{
    static PUT(url, {method = 'PUT', body}, callback){
        call({url: url + '/', method, body}).then(res => callback(res))
    }
}

function flash(element, response){
    if (response != element.value) {
        element.value = response
        return
    }
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

function formatDate(start, end = new Date()){
    if (end == null) return '---'
    if (start == null) return '---'
    difference = (end - new Date(start))/1000
    if (difference < 0) difference = (new Date() - new Date(start))/1000
    if (difference < 60) {
        return `${Math.floor(difference)} second(s) ago`;
    } else if (difference < 3600) {
        return `${Math.floor(difference / 60)} minute(s) ago`;
    } else if (difference < 86400) {
        return `${Math.floor(difference / 3600)} hour(s) ago`;
    } else if (difference < 2620800) {
        return `${Math.floor(difference / 86400)} day(s) ago`;
    } else if (difference < 31449600) {
        return `${Math.floor(difference / 2620800)} month(s) ago`;
    }
    return `${Math.floor(difference / 31449600)} year(s) ago`;
}