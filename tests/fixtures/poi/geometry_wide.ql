[out:json][timeout:15];
(
  nwr(around:1500,0,0)[~"^(shop|amenity|office|healthcare)$"~"."];
  nwr(around:1500,0,0)["atm"="yes"];
  nwr(around:1500,0,0)["man_made"="surveillance"];
);
(._; >>;);
out body;
