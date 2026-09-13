/* Reference globe: Natural Earth land; explicitly illustrative territory. No game API. */
(function(){
 'use strict';
 const ns='http://www.w3.org/2000/svg',rad=Math.PI/180,lat0=30*rad,lon0=15*rad;
 function project(point){const lat=point[1]*rad,lon=point[0]*rad-lon0;
  return [500+448*Math.cos(lat)*Math.sin(lon),500-448*(Math.cos(lat0)*Math.sin(lat)-Math.sin(lat0)*Math.cos(lat)*Math.cos(lon)),Math.sin(lat0)*Math.sin(lat)+Math.cos(lat0)*Math.cos(lat)*Math.cos(lon)];}
 function node(tag,attrs,parent){const n=document.createElementNS(ns,tag);Object.keys(attrs).forEach(k=>n.setAttribute(k,attrs[k]));parent.appendChild(n);return n;}
 function path(points,closed){let d='',open=false,all=true;points.forEach(point=>{const p=project(point);if(p[2]<0){open=false;all=false;return;}d+=(open?'L':'M')+p[0].toFixed(2)+','+p[1].toFixed(2);open=true;});return d+(closed&&all?'Z':'');}
 const grid=document.getElementById('graticule');
 for(let lat=-75;lat<=75;lat+=15){const points=[];for(let lon=-180;lon<=180;lon+=2)points.push([lon,lat]);node('path',{d:path(points,false)},grid);}
 for(let lon=-180;lon<180;lon+=15){const points=[];for(let lat=-90;lat<=90;lat+=2)points.push([lon,lat]);node('path',{d:path(points,false)},grid);}
 const territory=document.getElementById('territory'),corners=[[-3,57],[29,37],[-12,28]].map(project);
 node('polygon',{points:corners.map(p=>p[0]+','+p[1]).join(' ')},territory);
 corners.forEach((p,i)=>{node('circle',{cx:p[0],cy:p[1],r:23,class:'world-node-halo'},territory);node('circle',{cx:p[0],cy:p[1],r:7,class:'world-node-ring'},territory);node('circle',{cx:p[0],cy:p[1],r:3.5,class:'world-node-core'},territory);node('text',{x:p[0]+13,y:p[1]-13},territory).textContent='0'+(i+1);});
 fetch('world-land.geojson').then(r=>{if(!r.ok)throw Error('land');return r.json();}).then(data=>{
  const land=document.getElementById('land');data.features.forEach(feature=>{const g=feature.geometry;const polygons=g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[];
   polygons.forEach(polygon=>polygon.forEach(ring=>{const d=path(ring,true);if(d)node('path',{d,fill:ring.every(p=>project(p)[2]>=0)?'#162c2044':'none'},land);}));});
  document.getElementById('world-load').textContent='KONTURY LĄDÓW / NATURAL EARTH';
 }).catch(()=>{document.getElementById('world-load').textContent='KONTURY NIEDOSTĘPNE / SIATKA GLOBU';});
 window.addEventListener('message',event=>{if(event.origin!==location.origin||event.source!==window.parent)return;if(!['world-territory','world-trace'].includes(event.data))return;const trace=event.data==='world-trace';document.querySelector('.world-scene').dataset.view=trace?'trace':'territory';document.getElementById('world-state').textContent=trace?'ŚLAD / GEOMETRIA POZOSTAJE':'GRANICE / PERSPEKTYWA GLOBALNA';});
})();
