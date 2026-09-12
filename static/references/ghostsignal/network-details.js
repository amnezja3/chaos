/* Reference adapter for the same UI helper used by the show. */
(function () {
 const field=document.querySelector('.network-field'),data=document.getElementById('network-catalog');
 if (!field || !data || !window.GhostSignalNetworkDetails) return;
 window.GhostSignalNetworkDetails.mount({document,window,field,catalog:JSON.parse(data.textContent),parts:Array.from(field.querySelectorAll('.part'))});
})();
