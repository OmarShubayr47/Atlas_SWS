FeatureScript 3083;
import(path : "onshape/std/common.fs", version : "3083.0");

// Complete-enclosure rack prototype for A1 / PLA. No verified load rating.
// 120 x90 x8 platform; exactly TWO horizontal insertion sticks in ONE column.
// Both sticks share X=0, centres Z=26 and87: vertical pitch61, no side-by-side rack holes.
// 60 mm reach fromY34; 2 mm rim-to-tip retaining-hole stock.
// Owner: opposed 5 x 24.8 slots, vertical clear gap36.2 => pitch61;
// 51.3 interpreted as opposing-face span, measurement datums still unconfirmed.
export const SLOT_PITCH = { (millimeter) : [55,61,70] } as LengthBoundSpec;
export const POST_SPAN = { (millimeter) : [40,51.3,80] } as LengthBoundSpec;
export const BAR_WIDTH = { (millimeter) : [3.8,4.2,4.5] } as LengthBoundSpec;
export const SHELF_SLIDE = { (millimeter) : [0,0,110] } as LengthBoundSpec;

function makeBox(context is Context,id is Id,x,y,z,sx,sy,sz) returns Query
{
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(0,0,z)*millimeter,vector(0,0,1))});
    skRectangle(s,"r",{"firstCorner":vector(x,y)*millimeter,"secondCorner":vector(x+sx,y+sy)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":sz*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function roundPlate(context is Context,id is Id,origin,normal,u,x,y,sx,sy,depth,r) returns Query
{
    var a=r/sqrt(2);
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(origin*millimeter,normal,u)});
    skLineSegment(s,"b",{"start":vector(x+r,y)*millimeter,"end":vector(x+sx-r,y)*millimeter});
    skArc(s,"br",{"start":vector(x+sx-r,y)*millimeter,"mid":vector(x+sx-r+a,y+r-a)*millimeter,"end":vector(x+sx,y+r)*millimeter});
    skLineSegment(s,"r",{"start":vector(x+sx,y+r)*millimeter,"end":vector(x+sx,y+sy-r)*millimeter});
    skArc(s,"tr",{"start":vector(x+sx,y+sy-r)*millimeter,"mid":vector(x+sx-r+a,y+sy-r+a)*millimeter,"end":vector(x+sx-r,y+sy)*millimeter});
    skLineSegment(s,"t",{"start":vector(x+sx-r,y+sy)*millimeter,"end":vector(x+r,y+sy)*millimeter});
    skArc(s,"tl",{"start":vector(x+r,y+sy)*millimeter,"mid":vector(x+r-a,y+sy-r+a)*millimeter,"end":vector(x,y+sy-r)*millimeter});
    skLineSegment(s,"l",{"start":vector(x,y+sy-r)*millimeter,"end":vector(x,y+r)*millimeter});
    skArc(s,"bl",{"start":vector(x,y+r)*millimeter,"mid":vector(x+r-a,y+r-a)*millimeter,"end":vector(x+r,y)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":normal,"endBound":BoundingType.BLIND,"endDepth":depth*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function rod(context is Context,id is Id,x,y,z,r,h) returns Query
{
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(0,0,z)*millimeter,vector(0,0,1))});
    skCircle(s,"c",{"center":vector(x,y)*millimeter,"radius":r*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":h*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function subtract(context is Context,id is Id,target is Query,tool is Query)
{
    opBoolean(context,id,{"targets":target,"tools":tool,"operationType":BooleanOperationType.SUBTRACTION});
}
function join(context is Context,id is Id,bodies is array)
{
    opBoolean(context,id,{"tools":qUnion(bodies),"operationType":BooleanOperationType.UNION});
}
function label(context is Context,q is Query,name is string)
{
    setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":name});
}
function noPenetration(context is Context,a is Query,b is Query,message is string)
{
    for(var clash in evCollision(context,{"tools":a,"targets":b}))
        if(clash["type"]==ClashType.INTERFERE || clash["type"]==ClashType.TARGET_IN_TOOL || clash["type"]==ClashType.TOOL_IN_TARGET)
            throw regenError(message);
}
function gusset(context is Context,id is Id,x) returns Query
{
    // Broad support below the shelf; the top remains flat for either payload.
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(x,0,0)*millimeter,vector(1,0,0),vector(0,1,0))});
    skLineSegment(s,"a",{"start":vector(-40,0)*millimeter,"end":vector(30,0)*millimeter});
    skLineSegment(s,"b",{"start":vector(30,0)*millimeter,"end":vector(30,-26)*millimeter});
    skLineSegment(s,"c",{"start":vector(30,-26)*millimeter,"end":vector(-40,0)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(1,0,0),"endBound":BoundingType.BLIND,"endDepth":6*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function rackSlot(context is Context,id is Id,rearY,zc) returns Query
{
    // Assumed capsule ends for mockup only; actual slot shape remains to check.
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(0,rearY,0)*millimeter,vector(0,-1,0),vector(1,0,0))});
    var lo=zc-12.4;
    var hi=zc+12.4;
    skLineSegment(s,"l",{"start":vector(-2.5,lo+2.5)*millimeter,"end":vector(-2.5,hi-2.5)*millimeter});
    skArc(s,"t",{"start":vector(-2.5,hi-2.5)*millimeter,"mid":vector(0,hi)*millimeter,"end":vector(2.5,hi-2.5)*millimeter});
    skLineSegment(s,"r",{"start":vector(2.5,hi-2.5)*millimeter,"end":vector(2.5,lo+2.5)*millimeter});
    skArc(s,"b",{"start":vector(2.5,lo+2.5)*millimeter,"mid":vector(0,lo)*millimeter,"end":vector(-2.5,lo+2.5)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,-1,0),"endBound":BoundingType.BLIND,"endDepth":2.4*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}

function axisRod(context is Context,id is Id,p,axis,u,r,depth) returns Query
{
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(p*millimeter,axis,u)});
    skCircle(s,"c",{"center":vector(0,0)*millimeter,"radius":r*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":axis,"endBound":BoundingType.BLIND,"endDepth":depth*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function sideArm(context is Context,id is Id,x,H) returns Query
{
    var pts=[vector(-56,0),vector(18.4,0),vector(18.4,H),vector(34,H),vector(34,-34),vector(-56,-8)];
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(x,0,0)*millimeter,vector(1,0,0),vector(0,1,0))});
    for(var k=0;k<size(pts);k+=1)
        skLineSegment(s,"p"~k,{"start":pts[k]*millimeter,"end":pts[(k+1)%size(pts)]*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(1,0,0),"endBound":BoundingType.BLIND,"endDepth":8*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function topClamp(context is Context,id is Id,front is boolean) returns Query
{
    var cy=front ? -42 : 14;
    var ey=front ? -55 : 12.5;
    var ed=front ? 14.5 : 12.5;
    var bar=makeBox(context,id+"bar",-60,cy-1.5,62,120,3,6);
    var parts=[bar];
    for(var x in [-55,55])
    {
        parts=append(parts,roundPlate(context,id+("ear"~x),vector(0,0,62),vector(0,0,1),vector(1,0,0),x-5,ey,10,ed,6,2));
        parts=append(parts,rod(context,id+("foot"~x),x<0 ? -42.5 : 42.5,cy,60,2,2));
    }
    join(context,id+"join",parts);
    for(var x in [-55,55])
        subtract(context,id+("bolt"~x),bar,rod(context,id+("tool"~x),x,front ? -50 : 20,61.9,2.2,6.2));
    return bar;
}
annotation { "Feature Type Name" : "SWS complete enclosure rack" }
export const piRackCarrier=defineFeature(function(context is Context,id is Id,definition is map)
    precondition
    {
        annotation {"Name":"Rack slot pitch - owner61"}
        isLength(definition.pitch,SLOT_PITCH);
        annotation {"Name":"Opposed-face span - owner51.3 datum unconfirmed"}
        isLength(definition.span,POST_SPAN);
        annotation {"Name":"Bar and hanger thickness - trial fit in5 mm slot"}
        isLength(definition.barWidth,BAR_WIDTH);
        annotation {"Name":"Show complete-system enclosure/rack references","Default":true}
        definition.showReferences is boolean;
        annotation {"Name":"Print layout - parts individually; references removed","Default":false}
        definition.printLayout is boolean;
        annotation {"Name":"Include separate empty rack fit piece - NOT an extra rack attachment","Default":false}
        definition.coupon is boolean;
    }
    {
        var P=definition.pitch/millimeter;
        var D=definition.span/millimeter;
        var W=definition.barWidth/millimeter;
        var H=P+39;
        var reach=D+8.7;
        var tip=34+reach;
        var barBottom=21;
        var centres=[26,26+P];
        var crossY=tip-3.5;
        var keeperY=34.2+D+0.25;
        // Separate uniform-thickness hanger can be printed flat on its side.
        var hanger=makeBox(context,id+"hanger",-W/2,18.4,-34,W,13.6,H+34);
        var sticks=[];
        var n=0;
        for(var zc in centres)
        {
            subtract(context,id+("stickWindow"~n),hanger,makeBox(context,id+("stickWindowTool"~n),-W/2-0.1,22,zc-10.2,W+0.2,10.1,20.4));
            var stick=makeBox(context,id+("stickRoot"~n),-W/2,22.2,zc-10,W,9.8,20);
            var bar=makeBox(context,id+("bar"~n),-W/2,31.8,zc-5,W,tip-31.8,10);
            join(context,id+("stickJoin"~n),[stick,bar]);
            var roots=[];
            for(var zz in [zc-5,zc+5])
                roots=append(roots,qContainsPoint(qOwnedByBody(stick,EntityType.EDGE),vector(0,32,zz)*millimeter));
            opFillet(context,id+("rootRounds"~n),{"entities":qUnion(roots),"radius":1.5*millimeter});
            subtract(context,id+("retain"~n),stick,axisRod(context,id+("retainTool"~n),vector(-W/2-0.1,crossY,zc),vector(1,0,0),vector(0,1,0),1.5,W+0.2));
            subtract(context,id+("stickBolt"~n),stick,axisRod(context,id+("stickBoltTool"~n),vector(-W/2-0.1,27,zc),vector(1,0,0),vector(0,1,0),2.2,W+0.2));
            sticks=append(sticks,stick);
            n+=1;
        }
        subtract(context,id+"hangerBolt",hanger,axisRod(context,id+"hangerBoltTool",vector(-W/2-0.1,26,-22),vector(1,0,0),vector(0,1,0),2.2,W+0.2));
        // Independent upright restraint anchors: hardware/strap must be selected.
        for(var z in [42,58])
            subtract(context,id+("tie"~z),hanger,roundPlate(context,id+("tieTool"~z),vector(-W/2-0.1,0,0),vector(1,0,0),vector(0,1,0),22,z,7,5,W+0.2,1));
        var arms=[];
        n=0;
        for(var x in [-W/2-8,W/2])
        {
            var arm=sideArm(context,id+("arm"~n),x,H);
            for(var z in [-22,26,P+26])
                subtract(context,id+("armBolt"~n~z),arm,axisRod(context,id+("armBoltTool"~n~z),vector(x-0.1,z<0 ? 26 : 27,z),vector(1,0,0),vector(0,1,0),2.2,8.2));
            for(var y in [-50,10])
            {
                subtract(context,id+("floorArm"~n~y),arm,rod(context,id+("floorArmTool"~n~y),x+4,y,-34.1,2.2,34.2));
                var seat=y<0 ? -5.5 : -22.8;
                subtract(context,id+("nutSeat"~n~y),arm,makeBox(context,id+("nutSeatTool"~n~y),x-0.1,y-5,-34.1,8.2,10,seat+34.1));
            }
            arms=append(arms,arm);
            n+=1;
        }
        var platform=roundPlate(context,id+"floor",vector(0,0,0),vector(0,0,1),vector(1,0,0),-60,-56,120,90,8,4);
        subtract(context,id+"spineNotch",platform,makeBox(context,id+"spineNotchTool",-W/2-8.3,18.1,-0.1,W+16.6,16.1,8.2));
        n=0;
        for(var x in [-W/2-4,W/2+4])
            for(var y in [-50,10])
            {
                subtract(context,id+("floorBolt"~n),platform,rod(context,id+("floorBoltTool"~n),x,y,-0.1,2.2,8.2));
                subtract(context,id+("headPocket"~n),platform,rod(context,id+("headPocketTool"~n),x,y,3.8,4.5,4.3));
                n+=1;
            }
        var floorBits=[platform];
        n=0;
        for(var x in [-37,37])
            for(var y in [-48.9,17.9])
            {
                floorBits=append(floorBits,makeBox(context,id+("stop"~n),x-6,y,8,12,3,2.5));
                n+=1;
            }
        join(context,id+"stopJoin",floorBits);
        var sideBits=[platform];
        n=0;
        for(var x in [-50.95,47.95])
            for(var y in [-42,10])
            {
                sideBits=append(sideBits,makeBox(context,id+("sideStop"~n),x,y,8,3,5,2.5));
                n+=1;
            }
        join(context,id+"sideStopJoin",sideBits);
        var columns=[];
        n=0;
        for(var x in [-55,55])
            for(var y in [-50,20])
            {
                subtract(context,id+("columnFloor"~n),platform,rod(context,id+("columnFloorTool"~n),x,y,-0.1,2.2,8.2));
                var col=rod(context,id+("column"~n),x,y,8,5,54);
                subtract(context,id+("columnBore"~n),col,rod(context,id+("columnBoreTool"~n),x,y,7.9,2.2,54.2));
                columns=append(columns,col);
                n+=1;
            }
        var clamps=[topClamp(context,id+"frontClamp",true),topClamp(context,id+"rearClamp",false)];
        var keeper=roundPlate(context,id+"keeper",vector(0,keeperY+3,0),vector(0,-1,0),vector(1,0,0),-9,barBottom-5,18,P+20,3,2);
        n=0;
        for(var z in centres)
        {
            subtract(context,id+("keeperSlot"~n),keeper,roundPlate(context,id+("keeperTool"~n),vector(0,keeperY+3.1,0),vector(0,-1,0),vector(1,0,0),-W/2-0.3,z-5.3,W+0.6,10.6,3.2,0.5));
            n+=1;
        }
        var printed=[platform,hanger,arms[0],arms[1],keeper];
        for(var col in columns) printed=append(printed,col);
        for(var clamp in clamps) printed=append(printed,clamp);
        for(var stick in sticks) printed=append(printed,stick);
        label(context,platform,"01 Enclosure cradle120 x90 x8 - corner stops - flush M4 head pockets");
        label(context,hanger,"02 Central spine - single vertical rack-hole column - SIDE-FLAT print");
        label(context,arms[0],"03 Left triangular arm8 thick - SIDE-FLAT print");
        label(context,arms[1],"04 Right triangular arm8 thick - SIDE-FLAT print");
        label(context,keeper,"05 Rear keeper3 thick - retain pins and independent upright restraint");
        n=0;
        for(var col in columns) {label(context,col,"0"~(6+n)~" Clamp spacer10 OD x54 - M4 through bolt");n+=1;}
        label(context,clamps[0],"10 Front lid-perimeter clamp - print wide top face DOWN");
        label(context,clamps[1],"11 Rear lid-perimeter clamp - print wide top face DOWN");
        label(context,sticks[0],"12 LOWER horizontal insertion stick - X0 Z26 -60 reach -3 mm retaining hole");
        label(context,sticks[1],"13 UPPER horizontal insertion stick - X0 Z"~(26+P)~" -"~P~" above lower stick");
        // Full enclosure shape bounds, with knob and caps as separate references.
        var enclosure=roundPlate(context,id+"enclosure",vector(0,0,8),vector(0,0,1),vector(1,0,0),-47.45,-45.4,94.9,62.8,52,4.2);
        var knob=rod(context,id+"knobRef",-28,-26,68.5,10,14);
        var ptt=makeBox(context,id+"pttRef",-6.1,-32.1,60,12.2,12.2,4.9);
        var power=rod(context,id+"powerRef",28,-24,60,4.9,0.3);
        var reset=rod(context,id+"resetRef",28,-36,60,3,1);
        var refs=[enclosure,knob,ptt,power,reset];
        label(context,enclosure,"REFERENCE complete enclosure94.9 x62.8 x52 - estimated system payload305 g");
        label(context,knob,"REFERENCE nominal installed encoder knob -6.2 bore selected from owner coupon");
        label(context,ptt,"REFERENCE PTT cap - actual seating unverified");
        label(context,power,"REFERENCE power face - actual seating unverified");
        label(context,reset,"REFERENCE reset cap - actual switch height unverified");
        var faces=[];
        var rackFaceTop=26+P+12.4+2;
        n=0;
        for(var frontY in [34.2,34.2+D-2])
        {
            var face=makeBox(context,id+("rackFace"~n),-25.65,frontY,-34,51.3,2,rackFaceTop+34);
            var j=0;
            for(var z in [26,26+P])
            {
                subtract(context,id+("rackCut"~n~j),face,rackSlot(context,id+("rackTool"~n~j),frontY+2.1,z));
                j+=1;
            }
            label(context,face,"REFERENCE ONLY metal rack face - top slot edge stock2 mm - NOT a print part");
            faces=append(faces,face);
            refs=append(refs,face);
            n+=1;
        }
        for(var a=0;a<size(printed);a+=1)
        {
            noPenetration(context,printed[a],qUnion([enclosure,knob,ptt,power,reset]),"Printed rack part interferes with enclosure/control reference.");
            noPenetration(context,printed[a],qUnion(faces),"Printed rack part interferes with assumed rack faces.");
            for(var b=0;b<a;b+=1)
                noPenetration(context,printed[a],printed[b],"Rack printed parts interfere.");
        }
        // Display-only openings mirror the unchanged T-005 lid dimensions/positions.
        // Collision guards above use the FULL outer enclosure envelope first.
        // These shallow reference pockets are not the actual detailed enclosure.
        subtract(context,id+"refPttCut",enclosure,makeBox(context,id+"refPttTool",-6.4,-32.4,57.9,12.8,12.8,2.2));
        for(var hole in [vector(-28,-26,3.25),vector(28,-24,5.2),vector(28,-36,3.3)])
            subtract(context,id+("refGuide"~hole[0]~hole[1]),enclosure,rod(context,id+("refGuideTool"~hole[0]~hole[1]),hole[0],hole[1],57.9,hole[2],2.2));
        for(var side in [-1,1])
        {
            for(var row=0;row<5;row+=1)
                subtract(context,id+("refSpeaker"~side~row),enclosure,roundPlate(context,id+("refSpeakerTool"~side~row),vector(0,0,57.9),vector(0,0,1),vector(1,0,0),side*23.5-13.5,-9.7+row*4,27,2.4,2.2,1));
            subtract(context,id+("refVent"~side),enclosure,roundPlate(context,id+("refVentTool"~side),vector(0,0,57.9),vector(0,0,1),vector(1,0,0),side*3-1.5,-7,3,16,2.2,1));
        }
        if(definition.coupon)
        {
            var coupon=makeBox(context,id+"couponBack",81,24,10,18,10,30);
            var cb=makeBox(context,id+"couponBar",90-W/2,31.8,20,W,tip-31.8,10);
            join(context,id+"couponJoin",[coupon,cb]);
            subtract(context,id+"couponHole",coupon,axisRod(context,id+"couponTool",vector(90-W/2-0.1,crossY,25),vector(1,0,0),vector(0,1,0),1.5,W+0.2));
            label(context,coupon,"14 OPTIONAL empty fit piece - NOT mounted -60 datum reach");
            printed=append(printed,coupon);
        }
        var solidGrams=evVolume(context,{"entities":qUnion(printed)})/(millimeter*millimeter*millimeter)*0.00124;
        // Every print body is oriented and checked separately against A1 limits.
        if(definition.printLayout)
        {
            opDeleteBodies(context,id+"hideRefs",{"entities":qUnion(refs)});
            var side=matrix([[0,1,0],[0,0,1],[1,0,0]]);
            var flatKeeper=matrix([[1,0,0],[0,0,1],[0,-1,0]]);
            var flip=matrix([[1,0,0],[0,-1,0],[0,0,-1]]);
            var rotations=[identityMatrix(3),side,side,side,flatKeeper];
            for(var col in columns) rotations=append(rotations,identityMatrix(3));
            for(var clamp in clamps) rotations=append(rotations,flip);
            for(var stick in sticks) rotations=append(rotations,side);
            if(definition.coupon) rotations=append(rotations,side);
            for(var k=0;k<size(printed);k+=1)
            {
                opTransform(context,id+("orient"~k),{"bodies":printed[k],"transform":transform(rotations[k],vector(0,0,0)*millimeter)});
                var bb=evBox3d(context,{"topology":printed[k],"tight":true});
                var dims=(bb.maxCorner-bb.minCorner)/millimeter;
                if(dims[0]>240 || dims[1]>240 || dims[2]>240)
                    throw regenError("A print part exceeds conservative240 mm A1 single-part bounds.");
                var move=vector((k%3)*170,floor(k/3)*170,0)*millimeter-bb.minCorner;
                opTransform(context,id+("layout"~k),{"bodies":printed[k],"transform":transform(move)});
            }
        }
        else if(!definition.showReferences)
            opDeleteBodies(context,id+"hideRefs",{"entities":qUnion(refs)});
        reportFeatureInfo(context,id,"Complete-enclosure rack: exactly TWO horizontal insertion sticks, both X0, centres Z26 and"~(26+P)~", vertical pitch"~P~". No side-by-side rack holes. Guarded solid fits pass;"~reach~" mm reach and3 mm transverse retaining holes with2 mm rim stock. Metal-rack REFERENCE top slot edge stock2 mm; reference plates are not print parts.13 structural print parts plus optional fit piece. Solid PLA planning mass "~round(solidGrams)~" g at1.24 g/cm3; system estimate305 g, payload allowance500 g, total rack-load DESIGN TARGET2 kg, not tested capacity. Export print layout parts INDIVIDUALLY for A1. Actual hardware, rack/plug fit, PLA creep/temperature and loaded proof test remain required.");
    });
