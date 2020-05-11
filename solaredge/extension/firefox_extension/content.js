var customScript = `
Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

var getParameter = WebGLRenderingContext.getParameter;
WebGLRenderingContext.prototype.getParameter = parameter => {
    if (parameter === 37445) {
        return 'Intel Open Source Technology Center';
    }
    if (parameter === 37446) {
        return 'Mesa DRI Intel(R) Ivybridge Mobile ';
    }

    return getParameter(parameter);
};

['height', 'width'].forEach(property => {
    var imageDescriptor = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, property);
    Object.defineProperty(HTMLImageElement.prototype, property, {
        ...imageDescriptor,
        get: () => {
            if (this.complete && this.naturalHeight == 0) {
                return 20;
            }
            return imageDescriptor.get.apply(this);
        },
    });
});

var originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = parameters => (
    parameters.name === 'notifications' ?
        Promise.resolve({ state: Notification.permission }) :
        originalQuery(parameters)
);
function __sleep(milliseconds) {
    const date = Date.now();
    let currentDate = null;
    do {
        currentDate = Date.now();
    } while (currentDate - date < milliseconds);
}
function __compare_dates(last_scarp_date, post_date) {
    var date = new Date(parseInt(post_date) * 1000);
    return date > last_scarp_date;
}
function __parseQuery(queryString) {
    var query = {};
    var pairs = (queryString[0] === '?' ?
        queryString.substr(1) :
        queryString).split('&');
    for (var i = 0; i < pairs.length; i++) {
        var pair = pairs[i].split('=');
        query[decodeURIComponent(pair[0])] = decodeURIComponent(pair[1] || '');
    }
    return query;
}
function __intercept_url__call(url) {
    var HOSTS = ['monitoringpublic.solaredge.com'],
        PATHS = ['/solaredge-apigw/api/sites/1047995/layout/energy'],
        _url = new URL(window.origin + url);
    if (HOSTS.includes(_url.host)) {
        if (PATHS.includes(_url.pathname)) {
            return true
        }
        return false
    }
    return false;
}
function __process_scrap_response(data) { 
    window.scrap_response.push(data) 
}
function __scrap_data() {
    window.scrap_response = []
    element=document.getElementById('ext-comp-1034-button')
    if(element){element.click()}
}
function __get_data() {
    return { data: window.scrap_response }
}
if (typeof window.scrap_response === 'undefined') window.scrap_response = [];
if (typeof window.process_scrap_response === 'undefined') window.process_scrap_response = __process_scrap_response;

(function (XHR) {
    var open = XHR.prototype.open;
    var send = XHR.prototype.send;
    XHR.prototype.open = function (method, url, async, user, pass) {
        this._url = url;
        open.call(this, method, url, async, user, pass);
    };
    XHR.prototype.send = function (data) {
        var self = this,
            oldOnReadyStateChange,
            url = this._url;
        async function onReadyStateChange() {
            if (self.readyState == XHR.DONE) {
                var data;
                if ('object' == typeof self.response) {
                    const text = await self.response.text();
                    data = {
                        res: JSON.parse(text),
                        url: url,
                    };
                } else if (self.responseText) {
                    data = {
                        res: JSON.parse(self.responseText),
                        url: url,
                    };
                } else {
                    data = {
                        res: JSON.parse(self.response),
                        url: url,
                    };
                }
                __process_scrap_response(data);
                if (oldOnReadyStateChange) {
                    oldOnReadyStateChange();
                }
            }
        }
        var intercept = __intercept_url__call(url);
        if (intercept) {
            if (this.addEventListener) {
                this.addEventListener('readystatechange', onReadyStateChange, false);
            } else {
                oldOnReadyStateChange = this.onreadystatechange;
                this.onreadystatechange = onReadyStateChange;
            }
        }
        send.call(this, data);
    };
})(XMLHttpRequest);`;

function injectJs() {
    var script = document.createElement('script');
    script.innerHTML = customScript;
    script.type = 'text/javascript';
    script.id = '_ENGINE_';
    document.head.insertBefore(script, document.head.children[0]);
}
injectJs();
