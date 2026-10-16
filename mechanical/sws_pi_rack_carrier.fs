FeatureScript 3083;
// SUPERSEDED experimental Pi-base/sliding-shelf variant; not the live T-006 source.
// Current complete-enclosure, single-column two-stick design: sws_rack_enclosure_carrier.fs.
import(path : "onshape/std/common.fs", version : "3083.0");

// Rack-fitting corrected Pi5 base or larger box shelf slides into braced holder.
// 120 x90 x6 floor; enclosure footprint94.9 x62.8. Fit/load unverified.
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
annotation { "Feature Type Name" : "SWS rack shelf" }
export const piRackCarrier=defineFeature(function(context is Context,id is Id,definition is map)
    precondition
    {
        annotation {"Name":"Rack slot centre pitch - owner61 mm"}
        isLength(definition.pitch,SLOT_PITCH);
        annotation {"Name":"Opposing-face span - owner51.3 datum unconfirmed"}
        isLength(definition.span,POST_SPAN);
        annotation {"Name":"Through-bar width - trial fit in5 mm slot"}
        isLength(definition.barWidth,BAR_WIDTH);
        annotation {"Name":"Shelf withdrawal - zero is seated;110 is separate"}
        isLength(definition.shelfSlide,SHELF_SLIDE);
        annotation {"Name":"Use rack-fitting Pi5 base; off uses large box shelf","Default":true}
        definition.piBase is boolean;
        annotation {"Name":"Show payload and opposed rack-face references","Default":false}
        definition.showReferences is boolean;
        annotation {"Name":"Use enclosure envelope; off shows illustrative bare Pi","Default":true}
        definition.enclosureReference is boolean;
        annotation {"Name":"Show carrier before insertion - keeper separate","Default":false}
        definition.insertionPose is boolean;
        annotation {"Name":"Include separate empty slot/span test piece","Default":true}
        definition.coupon is boolean;
    }
    {
        var P=definition.pitch/millimeter;
        var D=definition.span/millimeter;
        var W=definition.barWidth/millimeter;
        var S=definition.shelfSlide/millimeter;
        // Default rear-spine-to-tip reach60 mm; retain8.7 mm beyond span.
        var reach=D+8.7;
        var slotCentres=[26,26+P];
        // Nominal insertion position; rounded ends will set actual gravity seating.
        var barBottom=26-12.4+1.6;
        var barCentres=[barBottom+5,barBottom+P+5];
        var keeperY=34+D+0.8;
        // Owner confirmed2 mm from hole rim to tip; radius1.5 => centre inset3.5.
        var crossY=34+reach-3.5;
        var tray;
        var shelfBodies=[];
        var n=0;
        if(definition.piBase)
        {
            // Inspected Feature Studio2 geometry, translated to rack pose.
            tray=roundPlate(context,id+"piBase",vector(0,0,0),vector(0,0,1),vector(1,0,0),-45.25,-43.2,90.5,58.4,2,2);
            shelfBodies=[tray];
            for(var x in [-39,19])
                for(var y in [-38.5,10.5])
                {
                    shelfBodies=append(shelfBodies,rod(context,id+("piPost"~n),x,y,2,1.25,5));
                    // Bearing collar gives a designed PCB underside seat atZ5;
                    // original diameter2.5 peg continues toZ7 through the Pi hole.
                    shelfBodies=append(shelfBodies,rod(context,id+("piSeat"~n),x,y,2,2.5,3));
                    n+=1;
                }
        }
        else
        {
            tray=roundPlate(context,id+"tray",vector(0,0,0),vector(0,0,1),vector(1,0,0),-60,-56,120,90,6,4);
            subtract(context,id+"rearNotch",tray,makeBox(context,id+"rearNotchTool",-47.3,27.7,-0.1,94.6,6.5,6.2));
            shelfBodies=[tray];
        }
        // Rear tabs/bridges enter the same receivers in either platform mode.
        var tabStart=definition.piBase ? 14.2 : 26.7;
        n=0;
        for(var x in [-35,35])
        {
            shelfBodies=append(shelfBodies,makeBox(context,id+("tongue"~n),x-6,tabStart,0,12,33.8-tabStart,6));
            n+=1;
        }
        join(context,id+"shelfJoin",shelfBodies);
        var spine=roundPlate(context,id+"spine",vector(0,34,0),vector(0,-1,0),vector(1,0,0),-14,-26,28,P+65,6,3);
        var beam=makeBox(context,id+"backBeam",-47,28,-26,94,6,38);
        var bodies=[spine,beam,gusset(context,id+"braceA",-44),gusset(context,id+"braceB",38)];
        var holder=spine;
        n=0;
        for(var z in [barBottom,barBottom+P])
        {
            bodies=append(bodies,makeBox(context,id+("bar"~n),-W/2,33.8,z,W,reach+0.2,10));
            n+=1;
        }
        join(context,id+"holderJoin",bodies);
        n=0;
        for(var x in [-35,35])
        {
            subtract(context,id+("receiver"~n),holder,roundPlate(context,id+("receiverTool"~n),vector(0,34.1,0),vector(0,-1,0),vector(1,0,0),x-6.3,-0.3,12.6,6.6,6.2,0.5));
            // Trial bolt holes align only when shelf is fully seated; hardware absent.
            subtract(context,id+("shelfBolt"~n),tray,rod(context,id+("shelfBoltTool"~n),x,31,-0.1,1.7,6.2));
            subtract(context,id+("holderBolt"~n),holder,rod(context,id+("holderBoltTool"~n),x,31,-26.1,1.7,38.2));
            n+=1;
        }
        n=0;
        if(!definition.piBase)
            for(var x in [-53,53])
                for(var y in [-30,14])
                {
                    subtract(context,id+("payloadTie"~n),tray,roundPlate(context,id+("payloadTieTool"~n),vector(0,0,-0.1),vector(0,0,1),vector(1,0,0),x-2.5,y-6,5,12,6.2,1));
                    n+=1;
                }
        n=0;
        for(var z in [barBottom,barBottom+P])
        {
            subtract(context,id+("crossHole"~n),holder,rod(context,id+("crossTool"~n),0,crossY,z-0.1,1.5,10.2));
            n+=1;
        }
        // Strap/cable-tie anchors in spine; use an independent upright restraint.
        n=0;
        for(var x in [-9,9])
        {
            subtract(context,id+("tieHole"~n),holder,roundPlate(context,id+("tieTool"~n),vector(0,34.1,0),vector(0,-1,0),vector(1,0,0),x-2.5,41,5,10,6.2,1));
            n+=1;
        }
        var keeper=roundPlate(context,id+"keeper",vector(0,keeperY+3,0),vector(0,-1,0),vector(1,0,0),-9,barBottom-5,18,P+20,3,2);
        n=0;
        for(var zc in barCentres)
        {
            subtract(context,id+("keeperSlot"~n),keeper,roundPlate(context,id+("keeperTool"~n),vector(0,keeperY+3.1,0),vector(0,-1,0),vector(1,0,0),-W/2-0.3,zc-5.3,W+0.6,10.6,3.2,0.5));
            n+=1;
        }
        label(context,tray,definition.piBase ? "Rack-fitting Pi5 base -58 x49 peg layout with bearing collars and rear tabs" : "Removable box shelf -120 x90 x6 with two12 x6 tongues - add retained bolts");
        label(context,holder,"Braced rack holder - two12.6 x6.6 shelf receivers - reach"~reach~" - fit/load unverified");
        label(context,keeper,"Rear retaining plate - add two retained crossbolts and upright tie - hardware unverified");
        var payload;
        if(!definition.piBase && definition.enclosureReference)
        {
            // Current source sleeve/lid footprint; conservative height includes nominal knob.
            payload=roundPlate(context,id+"envelope",vector(0,0,6),vector(0,0,1),vector(1,0,0),-47.45,-45.4,94.9,62.8,74.5,4.2);
            label(context,payload,"SWS enclosure94.9 x62.8 reference ONLY - conservative height74.5 - not actual assembly");
        }
        else
        {
            // Nominal reference pose only; real PCB bearing/retention/cooler absent.
            var piZ=definition.piBase ? 5 : 9;
            payload=makeBox(context,id+"pcb",-42.5,-42,piZ,85,56,1.276);
            n=0;
            for(var x in [-39,19])
                for(var y in [-24.5,24.5])
                {
                    subtract(context,id+("pcbHole"~n),payload,rod(context,id+("pcbTool"~n),x,y-14,piZ-0.1,1.35,1.5));
                    n+=1;
                }
            label(context,payload,"Bare Pi PCB85 x56 reference ONLY - actual bearing/retention unverified - cooler absent");
        }
        var faces=[];
        n=0;
        for(var frontY in [34.2,34.2+D-2])
        {
            var face=makeBox(context,id+("rackFace"~n),-25.65,frontY,0,51.3,2,P+45);
            var j=0;
            for(var zc in slotCentres)
            {
                subtract(context,id+("rackCut"~n~j),face,rackSlot(context,id+("rackTool"~n~j),frontY+2.1,zc));
                j+=1;
            }
            label(context,face,"Opposed rack face reference ONLY - assumed2 mm sheet and rounded slot ends");
            faces=append(faces,face);
            n+=1;
        }
        if(definition.insertionPose)
        {
            var move=transform(vector(0,-reach-5,0)*millimeter);
            opTransform(context,id+"carrierPose",{"bodies":tray,"transform":move});
            opTransform(context,id+"holderPose",{"bodies":holder,"transform":move});
            opTransform(context,id+"payloadPose",{"bodies":payload,"transform":move});
        }
        if(S>0)
        {
            var shelfMove=transform(vector(0,-S,0)*millimeter);
            opTransform(context,id+"shelfSlidePose",{"bodies":tray,"transform":shelfMove});
            opTransform(context,id+"payloadSlidePose",{"bodies":payload,"transform":shelfMove});
        }
        noPenetration(context,tray,payload,"Shelf interferes with payload reference.");
        noPenetration(context,tray,holder,"Removable shelf interferes with holder.");
        noPenetration(context,holder,payload,"Holder interferes with payload reference.");
        noPenetration(context,qUnion([tray,holder]),qUnion(faces),"Carrier interferes with assumed rack faces.");
        noPenetration(context,keeper,qUnion(faces),"Retaining plate interferes with assumed rack faces.");
        if(!definition.insertionPose)
            noPenetration(context,holder,keeper,"Retaining plate interferes with through-bars.");
        if(definition.coupon)
        {
            var coupon=makeBox(context,id+"couponBack",81,30,0,18,4,30);
            var couponBar=makeBox(context,id+"couponBar",90-W/2,33.8,10,W,reach+0.2,10);
            join(context,id+"couponJoin",[coupon,couponBar]);
            subtract(context,id+"couponCross",coupon,rod(context,id+"couponCrossTool",90,crossY,9.9,1.5,10.2));
            label(context,coupon,"Empty slot-span test piece - bar"~W~" x10 - reach"~reach~" - hole3 - test both rack faces first");
        }
        if(!definition.showReferences)
            opDeleteBodies(context,id+"hideReferences",{"entities":qUnion(append(faces,payload))});
        reportFeatureInfo(context,id,"Rack CAD: no guarded penetration. Platform is "~(definition.piBase ? "rack-fitting Pi5 base: original58 x49 peg layout, diameter5 bearing collars atZ5" : "large box shelf")~". Two12 x6 tabs in12.6 x6.6 receivers; trial diameter3.4 retained-bolt holes. Withdrawal "~S~". Bars "~W~" x10; reach "~reach~"; diameter3 holes with2 mm rim-to-tip stock. All fasteners, PCB retention, actual fit/cooler and print/load strength remain unverified.");
    });
