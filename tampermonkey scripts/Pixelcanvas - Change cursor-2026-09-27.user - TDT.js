// ==UserScript==
// @name         Pixelcanvas - Change cursor
// @namespace    http://tampermonkey.net/
// @version      2026-09-27
// @description  Change the cursor to cross when overing the canvas
// @author       TheDarkTiger, chatGPT
// @match        https://pixelcanvas.io/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=pixelcanvas.io
// @grant        none
// ==/UserScript==

(function () {
	'use strict';
	
	const style = document.createElement('style');
	
	style.textContent = `
		.maplibregl-canvas {
			cursor: default !important;
		}
	`;
	
	document.head.appendChild(style);
	
	console.log('Tampermonkey: Change cursor - Default cursor rule added');
})();
