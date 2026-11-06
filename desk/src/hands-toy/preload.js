'use strict';
const {contextBridge,ipcRenderer}=require('electron');let channel=null;ipcRenderer.on('hands-toy-channel',(_,c)=>{channel=c;});contextBridge.exposeInMainWorld('toy',{input:p=>{if(channel)ipcRenderer.send(channel,p);},frames:fn=>ipcRenderer.on('hands-toy-frame',(_,p)=>fn(p))});
