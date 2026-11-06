'use strict';
// Explicitly launched playground window; events go to its own world only.
const path=require('node:path');const {fork}=require('node:child_process');
function openPlayground({BrowserWindow,nodePath='node',onClose=()=>{}}){
 const win=new BrowserWindow({width:800,height:530,show:false,title:'Glim hands playground — fake data only',webPreferences:{preload:path.join(__dirname,'preload.js'),contextIsolation:true,nodeIntegration:false,sandbox:false}});
 const worker=fork(path.join(__dirname,'sandbox-worker.js'),[],{execPath:nodePath,stdio:['ignore','ignore','pipe','ipc'],env:{...process.env,ELECTRON_RUN_AS_NODE:'1'}});let closed=false;
 const {ipcMain}=require('electron');const channel='hands-toy-input:'+win.webContents.id;
 const receive=(e,p)=>{if(e.sender!==win.webContents||!p||closed)return;worker.send({op:'manual',packet:p});};ipcMain.on(channel,receive);
 win.webContents.on('did-finish-load',()=>{win.webContents.send('hands-toy-channel',channel);win.showInactive();});
 worker.on('message',m=>{if(!closed&&!win.isDestroyed())win.webContents.send('hands-toy-frame',m);});worker.on('error',()=>win.close());
 win.on('closed',()=>{closed=true;ipcMain.removeListener(channel,receive);worker.kill();onClose();});win.loadFile(path.join(__dirname,'playground.html'));return win;
}
module.exports={openPlayground};
