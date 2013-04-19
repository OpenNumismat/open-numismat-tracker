AmCharts.monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
AmCharts.shortMonthNames = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сент', 'Окт', 'Ноя', 'Дек'];
var vcolrow=0;
var vcolrowr=0;

//Выделяем ячейку колонку с ценой сохрана при наведении мыши
function SelPSohr(vname) {
	var els=document.getElementById(vname+'2');
	if (els.innerHTML.indexOf("&nbsp;")==-1) {
		for (var i=1; i<=3; i++)
		{
			els=document.getElementById(vname+i);
			els.style.backgroundColor='#fefbd8';
		}		
	}
}

//Снимаем выделение с колонки с ценой сохрана
function DeSelPSohr(vname) {
	var prizsohran=document.getElementById('prizsohran');
	if (prizsohran.title!=vname)
	{
		var els=document.getElementById(vname+'2');
		if (els.innerHTML.indexOf("&nbsp;")==-1) {
			for (var i=1; i<=3; i++)
			{
				els=document.getElementById(vname+i);
				els.style.backgroundColor='#FFFFFF';
			}		
		}
	}
}

//Определяем на сколько прокручена страница
var getPageScroll = (window.pageXOffset != undefined) ?
	function() {
		return {
			left: pageXOffset,
			top: pageYOffset
		};
	} :
	function() {
		var html = document.documentElement;
		var body = document.body;
		var top = html.scrollTop || body && body.scrollTop || 0;
		top -= html.clientTop;

		var left = html.scrollLeft || body && body.scrollLeft || 0;
		left -= html.clientLeft;

		return { top: top, left: left };
	}

//Меняем сохран
function FixSelPSohr(vname) {
	var els=document.getElementById(vname+'2');
	var prizsohran=document.getElementById('prizsohran');
	if ((els.innerHTML.indexOf("&nbsp;")==-1)&&(prizsohran.title!=vname))
	{
		var vvremimg=document.getElementById('vremimg');
		vvremimg.style.position="absolute";
		var scroll=getPageScroll();				
		vvremimg.style.left=scroll.left+document.body.clientWidth/2-16;
		vvremimg.style.top=scroll.top + document.body.clientHeight/2-16;
		vvremimg.style.display="inline";
		
		setTimeout(function (){					
			for (var i=1; i<=3; i++)
			{
				els=document.getElementById(vname+i);
				els.style.backgroundColor='#fefbd8';
			}
			var vtextsost=document.getElementById('textsost');
			vtextsost.innerHTML=vname.substr(1,vname.length);
			els=document.getElementsByName(prizsohran.title);
			for (i=1; i<=3; i++)
			{
				els=document.getElementById(prizsohran.title+i);
				els.style.backgroundColor='#FFFFFF';
			}
			for (i=chart.graphs.length-1; i>0; i--)
			{
				if (chart.graphs[i].valueField!='m')
				{
					chart.removeGraph(chart.graphs[i]);
				}
			}
			CreateAukGraphs(vname.substr(1,vname.length));
			
			//var vtableold=document.getElementById('table' + prizsohran.title.substr(1,prizsohran.title.length)+'p1');
			//vtableold.style.display="none";
			//var vtablenew=document.getElementById('table' + vname.substr(1,vname.length)+'p1');
			//vtablenew.style.display="inline";
			GoToPage(vname.substr(1,vname.length)+'p1');
					
			prizsohran.title=vname;
			vvremimg.style.display="none";
			var prizpage=document.getElementById('prizpage');				
			//prizpage.title=vname.substr(1,vname.length) + "p1";
		},50);
	}
}

//Создает новый набор точек аукциона		
function CreateAukGraph(vtitle, valuevild) {
	var graph = new AmCharts.AmGraph();
	graph.title = vtitle;
	graph.valueField = valuevild;
	graph.balloonText = "[[datcategory]]\nАукцион: " + vtitle + "\nЦена: [[value]] руб.";
	graph.bullet = "round";
	graph.lineAlpha = 0;
	graph.legendValueText=" ";
	chart.addGraph(graph);
}

//Переходит на строку прохода по клику на буллит
function handleClick(event)
{
	var mas=event.item.dataContext.u.split(',');
	var nameg=event.graph.valueField;
	for (var i=0; i<mas.length; i++) 
	{
		var mas1=mas[i].split(':');
		if (mas1[0]==nameg)
		{
			break;
		}
	}
	var vpriznecliarrow=document.getElementById('priznecliarrow');
	vpriznecliarrow.title='#rowid'+mas1[1];

	var vprizload=document.getElementById('prizload');
	if (GoToPage(mas1[2])==0)
	{
		vprizload.title='0';
		GoToRow(mas1[1]);
	}
	else
	{

		var vvremimg=document.getElementById('vremimg');
		vvremimg.style.position="absolute";
		var scroll=getPageScroll();				
		vvremimg.style.left=scroll.left+document.body.clientWidth/2-16;
		vvremimg.style.top=scroll.top + document.body.clientHeight/2-16;
		vvremimg.style.display="inline";

		vprizload.title=mas1[1];
	}

//	var prizsohran=document.getElementById('prizsohran');
//	var vtable;
//	if (document.getElementById('ttable' + prizpage.title).childNodes[0].tagName=="TBODY")
//	{
//		vtable=document.getElementById('ttable' + prizpage.title).childNodes[0].rows;
//	}
//	else
//	{
//		vtable=document.getElementById('ttable' + prizpage.title).childNodes[1].rows;
//	}
//	for (i=1; i<vtable.length; i++) 
//	{
//		DeSelRow(vtable[i].id);
//	}
//
//	window.location='#rowid'+mas1[1];
//	SelRow('rowid'+mas1[1]);
}

//Переходит на строку
function GoToRow(rowid)
{
	var prizsohran=document.getElementById('prizsohran');
	var prizpage=document.getElementById('prizpage');
	var vtable;
	if (document.getElementById('ttable' + prizpage.title).childNodes[0].tagName=="TBODY")
	{
		vtable=document.getElementById('ttable' + prizpage.title).childNodes[0].rows;
	}
	else
	{
		vtable=document.getElementById('ttable' + prizpage.title).childNodes[1].rows;
	}
	for (i=1; i<vtable.length; i++) 
	{
		DeSelRow(vtable[i].id);
	}

	window.location='#rowid'+rowid;
	SelRow('rowid'+rowid);
}

//Пытается перейти на строку после загрузок картинок
function MayGoToRow()
{
	vcolrowr=vcolrowr+1;
	//window.alert(vcolrowr +' '+vcolrow);
	if (vcolrowr==vcolrow)
	{
		vcolrowr=0;
		vcolrow=0;
		var vprizload=document.getElementById('prizload');
		//window.alert(vprizload.title);
		if (vprizload.title!='0')
		{
			document.getElementById('vremimg').style.display="none";
			GoToRow(vprizload.title);
		}
	}
}

//Выделяет строку
function SelCatRow(rowid)
{
	var vpriznecliarrow=document.getElementById('priznecliarrow');
	if (vpriznecliarrow.title!="")
	{
		vpriznecliarrow.title="";
	}
	else
	{
		SelRow(rowid);
	}
}	

//Снимает выделение со строки
function DeSelCatRow(rowid)
{
	DeSelRow(rowid);
}

//Выделяет ссылку на страницу
function SelLinkPage(idpage)
{
	var vzagl=document.getElementById(idpage);
	vzagl.color="#ff8903";
	vzagl.style.fontWeight='bold';
}

//Снимает выделение ссылки на страницу
function DeSelLinkPage(idpage)
{
	var vzagl=document.getElementById(idpage);
	vzagl.color="#5d85a9";
	vzagl.style.fontWeight='normal';
}

//Переходит на заданую страницу с лотами
function GoToPage(idpage)
{
	var prizpage=document.getElementById('prizpage');
	var pos=idpage.indexOf("qwe");
	var spage;
	if (pos>0)
	{
		pos=pos+3;
		spage=idpage.substr(pos,idpage.length-pos);
	}
	else
	{
		spage=idpage;
	}

	var vtable;
	if (document.getElementById('ttable' + prizpage.title).childNodes[0].tagName=="TBODY")
	{
		vtable=document.getElementById('ttable' + prizpage.title).childNodes[0].rows;
	}
	else
	{
		vtable=document.getElementById('ttable' + prizpage.title).childNodes[1].rows;
	}

	for (i=1; i<vtable.length; i++) 
	{
		DeSelRow(vtable[i].id);
	}

	var vtableold=document.getElementById('table' + prizpage.title);
	vtableold.style.display="none";
	var vtablenew=document.getElementById('table' + spage);
	if (vtablenew==null)
	{
		var vdiv = document.createElement('div');
		vdiv.id='table' + spage
		vdiv.onload=MayGoToRow;
		vdiv.style.display="inline";
		//window.alert(window.location.pathname);
		//window.alert(window.location.pathname.substr(window.location.pathname.indexOf('catalogcb/catalogcb')+19,window.location.pathname.length-window.location.pathname.indexOf('.asp')+1));
		//var idcoin=(window.location.split('/')[6]).split('.asp')[0];
		//window.alert(idcoin);
		//vdiv.innerHTML=VizovServerCat("http://localhost/web/catalog/catalogcb/catalogcb"+window.location.pathname.substr(window.location.pathname.indexOf('catalogcb/catalogcb')+19,window.location.pathname.length-window.location.pathname.indexOf('.asp')+1)+"p.asp?p="+spage);
		vdiv.innerHTML=VizovServerCat("http://www.fcoins.ru/catalog/catalogcb/catalogcb"+window.location.pathname.substr(window.location.pathname.indexOf('catalogcb/catalogcb')+19,window.location.pathname.length-window.location.pathname.indexOf('.asp')+1)+"p.asp?p="+spage);
		vtableold.parentNode.insertBefore(vdiv, vtableold);
		vcolrow=document.getElementById('ttable' + spage).childNodes[0].rows.length-1;
		vcolrowr=0;
		prizpage.title=spage;
		return 1;
	}
	else
	{
		vtablenew.style.display="inline";
		prizpage.title=spage;
		return 0;
	}
	//prizpage.title=spage;

//	if (vtablenew==null)
//	{

		//var vprizload=document.getElementById('prizload');
		//vprizload.title=0;
		//setTimeout(function (){					
		//	while (vprizload.title==0)
		//	{
		//		vprizload=document.getElementById('prizload');
		//	}
//
		//},50);
		//document.getElementById('vremimg').style.display="none";
//	}
}


//Cинхронный вызов серверной страницы
function VizovServerCat(surl)
{
	var xmlhttp = getXmlHttp()
	xmlhttp.open('GET', surl, false);
	//xmlhttp.overrideMimeType("text/html; charset=windows-1251");
	xmlhttp.send(null);
	if(xmlhttp.status == 200) {
		return xmlhttp.responseText;
	}
}