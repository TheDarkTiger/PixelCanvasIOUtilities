// ==UserScript==
// @name         Pixelcanvas - Change cursor
// @namespace    http://tampermonkey.net/
// @version      2025-08-18
// @description  Change the cursor to cross when overing the canvas
// @author       TheDarkTiger
// @match        https://pixelcanvas.io/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=pixelcanvas.io
// @grant        none
// ==/UserScript==

(function () {
	'use strict';
	
	// State of canvas research
	let canvasFound = false;
	
	// Function to check for canvas and buttons
	function checkForElements() {
		
		// Change cursor style of the canvas
		//function changeCursorStyle() {
		const canvas = document.querySelector( ".maplibregl-canvas" );
		if( !canvasFound && canvas ) {
			canvasFound = true;
			canvas.setAttribute( 'style', canvas.getAttribute('style') + ";cursor:crosshair;");
			console.log( "Tampermonkey script: Change cursor - Canvas cursor style changed!" );
			
			// Stop listening to evens
			clearInterval( timer );
			observer.disconnect();
			console.log( "Tampermonkey script: Change cursor - Should be good. Shuting down." );
		}else{
			console.log( "Tampermonkey script: Change cursor - Canvas not found..." );
		}
		//}
	}
	
	// Start checking immediately
	checkForElements();
	
	// Observe DOM changes for new elements
	const observer = new MutationObserver( checkForElements );
	
	// Start observing the document body
	observer.observe( document.body, {
		childList: true,
		subtree: true,
		attributeFilter: ['class', 'style'] // Optional: monitor class/style changes
	});
	
	// Optional: Polling fallback (in case observer misses elements)
	let timer = setInterval( checkForElements, 5000 );
})();