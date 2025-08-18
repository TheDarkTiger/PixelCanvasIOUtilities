// ==UserScript==
// @name         Pixelcanvas - Remove map buttons
// @namespace    http://tampermonkey.net/
// @version      2025-08-18
// @description  Removes map buttons
// @author       TheDarkTiger
// @match        https://pixelcanvas.io/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=pixelcanvas.io
// @grant        none
// ==/UserScript==

(function () {
	'use strict';
	
	// State of buttons tweak
	let buttonsRemoved = 0;
	
	// Function to check for canvas and buttons
	function checkForElements() {
		
		// Find and remove map buttons
		const buttons = document.querySelectorAll('div > button[class*="flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-md hover:bg-gray-100"]');
		if( (buttonsRemoved < 2) && buttons.length > 0) {
			
			buttons.forEach(button => {
				if( ["Explore a random city", "Go to my location"].includes( button.title ) )
				{
					const parentDiv = button.closest('div');
					if (parentDiv) {
						parentDiv.remove();
						console.log( "Tampermonkey script: Remove map buttons - Removed button '" + button.title + "' container!" );
						buttonsRemoved += 1;
					}
				}
			});
		}
		
		if( buttonsRemoved >= 2 ) {
			
			// Stop listening to evens
			clearInterval( timer );
			observer.disconnect();
			console.log( "Tampermonkey script: Remove map buttons - Should be good. Shuting down." );
		}else{
			console.log( "Tampermonkey script: Remove map buttons - Buttons not found..." );
		}
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