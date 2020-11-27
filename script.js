var data = {
	  "SourceFile"      : "{ImagePath}/{SourceFile}"
	, "ImageDescription": "{ImageDescription}"
	, "UserComment"     : `{UserComment}`
	, "Rating"          : "{Rating}"
}
if(window.location.hash)
	document.getElementById("StaticText").value = window.location.hash.substring(1);

setTags(data);

var myTags = 
{TagJsonData}
;

var div =  document.getElementById("tags");
for (var i in myTags){
	div.innerHTML += ""+ i +": ";
	var l = 0;
	for (var tagName in myTags[i]){
		var tag = myTags[i][tagName];
		div.innerHTML += (l==0 ? '':', ');
		div.innerHTML +=  '<a id="tag'+tag+'" class="small-text"  href="javascript:addTag(\''+tag+'\')">'+ tagName +'</a>';
		l++;
	}
	div.innerHTML += "<br>";
}

var saveBtn = document.getElementById("saveNext");
saveBtn.addEventListener("click", function(){callPostExif(event)});

function navigate(path){
	var staticText = document.getElementById("StaticText").value;
	if (path === "/")
		document.location = path +"#"+ staticText
	else
		document.location = path + data["SourceFile"]+"#"+ staticText
}
document.getElementById("linkPrev"     ).addEventListener("click", function(){ navigate("/nav/prev/"); });
document.getElementById("linkNext"     ).addEventListener("click", function(){ navigate("/nav/next/"); });
document.getElementById("linkUp"       ).addEventListener("click", function(){ navigate("/nav/up/"  ); });
document.getElementById("linkDel"      ).addEventListener("click", function(){ navigate("/del/"     ); });
document.getElementById("linkShutdown" ).addEventListener("click", function(){ document.location = "/shutdown"; });
document.getElementById("linkHome"     ).addEventListener("click", function(){ document.location = "/html";     });
document.getElementById("linkReload"   ).addEventListener("click", function(){ document.location.reload();      });

function handleKeyEvent(e){
	e = e || window.event;
	console.log('### '+ e.key +":"+ document.activeElement.tagName);
	var sourceTag = document.activeElement.tagName;
	if (sourceTag=="BODY") {
		if (e.key == "ArrowLeft" ) return navigate("/nav/prev/");
		if (e.key == "ArrowRight") return navigate("/nav/next/");
		if (e.key == "ArrowUp")    return navigate("/nav/up/");
		document.getElementById("UserComment").focus();
	}
	if (e.key == "Escape") {
			document.activeElement.blur();
	}	
}
window.addEventListener('keydown', function(){handleKeyEvent(event)});

function switchImage(event){
	var img = document.getElementById("image");
	if (img.classList.contains("img-resize")) {
		var scrollX = event.pageX *100 / img.clientWidth;
		var scrollY = event.pageY *100 / img.clientHeight;
		img.classList.remove("img-resize");
		img.classList.add   ("img-normal");
		scrollX = img.clientWidth  /100 * scrollX - event.pageX;
		scrollY = img.clientHeight /100 * scrollY - event.pageY;
		document.getElementById("imageContainer").scrollTo(scrollX,scrollY);
	} else {
		img.classList.remove("img-normal");
		img.classList.add   ("img-resize");
	}
}
document.getElementById("image" ).addEventListener("click", switchImage);


function repaintUserComment(){
	var key = window.event.keyCode;
	if (key === 13 || key===44) { 
		repaintTags(); 
		return false; 
	}
	return true; 
}

document.getElementById("UserComment").addEventListener("keypress",repaintUserComment );
document.getElementById("UserComment").addEventListener("blur"    ,repaintTags );

repaintTags();



function callPostExif(){
	var headers = ({'Content-Type': 'application/json'});
	var body = getTags();
	// Komma vorne + hinten fuer bessere Suche
console.log("#### uc: "+ body["UserComment"]);
	if (body["UserComment"]) body["UserComment"] = "," + body["UserComment"] +","
console.log("#### uc: "+ body["UserComment"]);
	body = JSON.stringify(body);
	fetch("http://127.0.0.1:5000/html/"+ encodeURI(data["SourceFile"])
		, { method: "POST", headers: headers, body: body }
	).then(  (res)  => { 
		return res.text().then( txt => {
			document.location = "/html/"+txt+"#"+ document.getElementById("StaticText").value;
		});
	})
	.catch( (err)  => { console.log("POST: "+ err) });
}


function getTags(){
	var uc = document.getElementById("UserComment"     ).value;
	var id = document.getElementById("ImageDescription").value;
	var st = document.getElementById("StaticText"      ).value;
	var rating = document.querySelector('input[name="Rating"]:checked').value
	return {'UserComment': uc,'ImageDescription': id, 'Rating': rating, 'StaticText': st};
}


function setTags(json){
	document.getElementById("ImageDescription").value = json["ImageDescription"];
	var rating = json["Rating"] || "0";
	document.getElementById("Rating"+rating).checked=true;

	var static = document.getElementById("StaticText").value
	var uc = json["UserComment"];
	if (static) {
		//console.log("STATIC "+static);
		if (uc) 
			uc = static +","+ uc;
		else 
			uc = static;
	}
	document.getElementById("UserComment"     ).value = uc;
	var list = getUserTags();
	document.getElementById("UserComment").value = list.sort(compareTrimed).join();
}


function getUserTags(){
	var uc = document.getElementById("UserComment").value;
	uc = uc.replace(", ",",")
	if (uc.charAt(0)==",") uc = uc.substring(1);
	uc = uc.split(",");
	return uc;
}
function setUserTags(tagList){
	var uc = document.getElementById("UserComment").value = tagList.join();
}



function addTag(tag){
	var list = getUserTags();
	const equalsIgnoreCase = (element) => element.toLowerCase().trim() === tag.toLowerCase();
	var idx = list.findIndex(equalsIgnoreCase);
	if (idx>=0) {
		list.splice(idx,1);
	} else {
		list.push(tag);
	}
	document.getElementById("UserComment").value = list.sort(compareTrimed).join();
	repaintTags();
}


function repaintTags(){
	var list = getUserTags();
	list = Array.from(new Set(list))
	setUserTags(list);

	for (var i in myTags){
		for (var j in myTags[i]){
			var tag = myTags[i][j];
			var elem = document.getElementById("tag"+tag);
			const equalsIgnoreCase = (element) => element.toLowerCase().trim() === tag.toLowerCase();
			var idx = list.findIndex(equalsIgnoreCase);
			if (idx>=0) {
				elem.classList.add("activeTag");
			} else {
				elem.classList.remove("activeTag");
			}
		}
	}
}

function compareTrimed(_a, _b) {
	var a = _a.trim();
	var b = _b.trim();
	var a1 = _a.charAt(1);
	var b1 = _b.charAt(1);
	if (a1==":" && b1!=":") return  1;
	if (a1!=":" && b1==":") return -1;
	if (a > b) return 1;
	if (b > a) return -1;
	return 0;
}


// make Divs moveable
var mousedown = false;

var divAttention     = document.getElementById('divAttention');
var divAttentionMove = document.getElementById('divAttentionMove');
divAttentionMove.addEventListener('mousedown', function (e) {
	mousedown = true;
	moveDiv = divAttention;
	x = divAttention.offsetLeft - e.clientX; 
	y = divAttention.offsetTop  - e.clientY; 
});
divAttention.addEventListener('mouseup', function (e) { mousedown = false; }, true); 

var divTitle = document.getElementById('divTitle');
var divTitleMove = document.getElementById('divTitleMove');
divTitleMove.addEventListener('mousedown', function (e) {
	mousedown = true;
	moveDiv = divTitle;
	x = divTitle.offsetLeft - e.clientX; 
	y = divTitle.offsetTop  - e.clientY; 
});
divTitle.addEventListener('mouseup', function (e) { mousedown = false; }, true); 

var divTags = document.getElementById('divTags');
var divTagsMove = document.getElementById('divTagsMove');
divTagsMove.addEventListener('mousedown', function (e) {
	 mousedown = true;
	 moveDiv = divTags;
	 x = divTags.offsetLeft - e.clientX; 
	 y = divTags.offsetTop  - e.clientY; 
});
divTags.addEventListener('mouseup', function (e) { mousedown = false; }, true); 

var divContainer = document.querySelector('.container');
divContainer.addEventListener('mousemove', function (e) { 
	 if (mousedown) { 
		 moveDiv.style.left = e.clientX + x + 'px'; 
		 moveDiv.style.top  = e.clientY + y + 'px';
	 } 
 }, true); 

// fix heigth
//divTitle    .setAttribute("style","height:"+ (divTitle     .offsetHeight -10) +"px");
//divTags     .setAttribute("style","height:"+ (divTags      .offsetHeight -10) +"px");
//divAttention.setAttribute("style","height:"+ (divAttention .offsetHeight -10) +"px");

