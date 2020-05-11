'use strict';
function onExecuted (result) {
  console.log (result);
}

function onError (error) {
  console.log (`Error: ${error}`);
}
function handleTab (tabId) {
  const executing = browser.tabs.executeScript (tabId, {file: '/content.js'});
  executing.then (onExecuted, onError);
}
var gettingActiveTab = browser.tabs.query ({active: true, currentWindow: true});
gettingActiveTab.then (tabs => {
  handleTab (tabs[0].id);
});

browser.tabs.onUpdated.addListener ((tabId, changeInfo, tab) => {
  if (!changeInfo.url) {
    return;
  }
  var ActiveTab = browser.tabs.query ({
    active: true,
    currentWindow: true,
  });
  ActiveTab.then (tabs => {
    if (tabId == tabs[0].id) {
      handleTab (tabId);
    }
  });
});

browser.tabs.onActivated.addListener (activeInfo => {
  handleTab (activeInfo.tabId);
});
