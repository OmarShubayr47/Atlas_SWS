FeatureScript 3083;
import(path : "onshape/std/common.fs", version : "3083.0");

// SWS mechanical prototype. Millimetres. Not fabrication-approved.
// Original base remains in Part Studio 1. This feature creates new parts only.
// Base outline inspected in CAD: 90.5 x 58.4, R2, 2 mm plate; printed fit unverified.
export const HEIGHT = { (millimeter) : [35, 50, 100] } as LengthBoundSpec;
export const FIT = { (millimeter) : [0.05, 0.2, 0.6] } as LengthBoundSpec;
export const KNOB_D = { (millimeter) : [16, 20, 28] } as LengthBoundSpec;
// Display offset only: zero seats the lid at the sleeve top.
export const LID_OFFSET = { (millimeter) : [0, 10, 30] } as LengthBoundSpec;
// Trial pocket/seat/wire dimensions are design choices, not measured housing fits.
export const PTT_POCKET = { (millimeter) : [6, 8.6, 10] } as LengthBoundSpec;
export const POWER_POCKET = { (millimeter) : [5, 8.4, 9] } as LengthBoundSpec;
export const ENC_POCKET_X = { (millimeter) : [11.9, 12.3, 13] } as LengthBoundSpec;
export const ENC_POCKET_Y = { (millimeter) : [12.2, 12.6, 13] } as LengthBoundSpec;
export const RESET_POCKET_X = { (millimeter) : [7.9, 9.2, 10] } as LengthBoundSpec;
export const RESET_POCKET_Y = { (millimeter) : [4.4, 4.8, 5] } as LengthBoundSpec;
export const PTT_SEAT = { (millimeter) : [5, 8, 14] } as LengthBoundSpec;
export const POWER_SEAT = { (millimeter) : [4, 6, 12] } as LengthBoundSpec;
export const ENC_SEAT = { (millimeter) : [4.5, 5, 8] } as LengthBoundSpec;
export const RESET_SEAT = { (millimeter) : [5.4, 9.1, 12] } as LengthBoundSpec;
export const RESET_TEST_SEAT = { (millimeter) : [4.8, 8.5, 10] } as LengthBoundSpec;
export const WIRE_PORT = { (millimeter) : [3, 6, 7] } as LengthBoundSpec;
// Existing corrected base has 2 mm plate + 5 mm posts: nominal PCB seat z7.
export const PI_SEAT = { (millimeter) : [5, 7, 12] } as LengthBoundSpec;

function prism(context is Context, id is Id, x, y, z, sx, sy, sz) returns Query
{
    var s = newSketchOnPlane(context, id + "s", {"sketchPlane" : plane(vector(0,0,z)*millimeter, vector(0,0,1))});
    skRectangle(s, "r", {"firstCorner" : vector(x,y)*millimeter, "secondCorner" : vector(x+sx,y+sy)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":sz*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function roundedPrism(context is Context, id is Id, x, y, z, sx, sy, sz, r) returns Query
{
    return roundedPlanePrism(context,id,vector(0,0,z),vector(0,0,1),vector(1,0,0),x,y,sx,sy,sz,r);
}
function roundedPlanePrism(context is Context, id is Id, origin, normal, u, x, y, sx, sy, sz, r) returns Query
{
    // Tangent quarter-arcs. Keep r below half either side to avoid zero-length lines.
    var a=r/sqrt(2);
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(origin*millimeter,normal,u)});
    skLineSegment(s,"bottom",{"start":vector(x+r,y)*millimeter,"end":vector(x+sx-r,y)*millimeter});
    skArc(s,"br",{"start":vector(x+sx-r,y)*millimeter,"mid":vector(x+sx-r+a,y+r-a)*millimeter,"end":vector(x+sx,y+r)*millimeter});
    skLineSegment(s,"right",{"start":vector(x+sx,y+r)*millimeter,"end":vector(x+sx,y+sy-r)*millimeter});
    skArc(s,"tr",{"start":vector(x+sx,y+sy-r)*millimeter,"mid":vector(x+sx-r+a,y+sy-r+a)*millimeter,"end":vector(x+sx-r,y+sy)*millimeter});
    skLineSegment(s,"top",{"start":vector(x+sx-r,y+sy)*millimeter,"end":vector(x+r,y+sy)*millimeter});
    skArc(s,"tl",{"start":vector(x+r,y+sy)*millimeter,"mid":vector(x+r-a,y+sy-r+a)*millimeter,"end":vector(x,y+sy-r)*millimeter});
    skLineSegment(s,"left",{"start":vector(x,y+sy-r)*millimeter,"end":vector(x,y+r)*millimeter});
    skArc(s,"bl",{"start":vector(x,y+r)*millimeter,"mid":vector(x+r-a,y+r-a)*millimeter,"end":vector(x+r,y)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":normal,"endBound":BoundingType.BLIND,"endDepth":sz*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function cylinder(context is Context, id is Id, x, y, z, r, depth) returns Query
{
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(0,0,z)*millimeter,vector(0,0,1))});
    skCircle(s,"c",{"center":vector(x,y)*millimeter,"radius":r*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":depth*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}
function cut(context is Context,id is Id,target is Query,tool is Query)
{
    opBoolean(context,id,{"targets":target,"tools":tool,"operationType":BooleanOperationType.SUBTRACTION});
}
function namePart(context is Context,q is Query,name is string)
{
    setProperty(context,{"entities":q,"propertyType":PropertyType.NAME,"value":name});
}
function wallWindow(context is Context,id is Id,shell is Query,face is string,c,hc,w,ht)
{
    // Prototype plug-access windows; official Pi5 STEP supplies connector datums,
    // not manufacturer panel cutouts. Actual plugs/recess fit must be tested.
    var origin=vector(44.9,0,0);
    var normal=vector(1,0,0);
    var u=vector(0,1,0);
    if(face=="front")
    {
        origin=vector(0,-28.8,0);
        normal=vector(0,-1,0);
        u=vector(1,0,0);
    }
    if(face=="left")
    {
        origin=vector(-44.9,0,0);
        normal=vector(-1,0,0);
        u=vector(0,-1,0);
        c=-c;
    }
    cut(context,id+"cut",shell,roundedPlanePrism(context,id,origin,normal,u,c-w/2,hc-ht/2,w,ht,3.2,0.8));
}
function speakerShelf(context is Context,id is Id,shell is Query,cx,H)
{
    // Sleeve-integral shelf: insert speakers from above before fitting the lid.
    // Owner body 35 x 25 x 6.2; trial .3 lateral and .4 front-face clearances.
    // Cantilever strength, housing bearing surfaces and wire fit are unverified.
    var floor=roundedPrism(context,id+"floor",cx-19,0.7,H-8.6,38,28.8,2,0.6);
    // Open +X wire notch: leads can drop below the floor and run toward HAT pads.
    cut(context,id+"notchCut",floor,prism(context,id+"notch",cx+15,10.5,H-8.7,4.2,6,2.2));
    var bodies=[shell,floor];
    bodies=append(bodies,prism(context,id+"leftWall",cx-19,0.7,H-6.7,1.2,25.7,3.3));
    bodies=append(bodies,prism(context,id+"rightWallA",cx+17.8,0.7,H-6.7,1.2,8.8,3.3));
    bodies=append(bodies,prism(context,id+"rightWallB",cx+17.8,17.5,H-6.7,1.2,8.9,3.3));
    // Overlap the side walls; an edge-only corner touch is non-manifold.
    bodies=append(bodies,prism(context,id+"northStop",cx-19,26.3,H-6.7,38,1.2,3.3));
    // A local south stop avoids the encoder cradle; tongue gives solid floor stock.
    var stopX=cx-17.5;
    if(cx<0)
        stopX=cx+11.5;
    bodies=append(bodies,prism(context,id+"stopTongue",stopX,-0.5,H-8.6,6,1.3,2));
    bodies=append(bodies,prism(context,id+"southStop",stopX,-0.5,H-6.7,6,1.2,3.3));
    for(var side in [-1,1])
    {
        var ribId=id+("rib"~side);
        var rib=prism(context,ribId,cx+side*10-1,0.7,H-14.6,2,28.8,6.1);
        // Continuous 6 wide x 4 high under-shelf wire corridor through both ribs.
        cut(context,ribId+"reliefCut",rib,prism(context,ribId+"relief",cx+side*10-1.1,10.5,H-14.7,2.2,6,4.1));
        bodies=append(bodies,rib);
    }
    opBoolean(context,id+"join",{"tools":qUnion(bodies),"operationType":BooleanOperationType.UNION});
    return shell;
}
function checkNoInterference(context is Context,tools is Query,targets is Query,label is string)
{
    // Contact at the cradle seat/posts is intended; solid penetration is not.
    // API: https://cad.onshape.com/FsDoc/library.html#ClashType
    for(var clash in evCollision(context,{"tools":tools,"targets":targets}))
        if(clash["type"]==ClashType.INTERFERE || clash["type"]==ClashType.TARGET_IN_TOOL || clash["type"]==ClashType.TOOL_IN_TARGET)
            throw regenError(label ~ " has solid interference.");
}
function mountingPosts(context is Context,id is Id,roof is Query,cx,cy,Z,S,mountX) returns Query
{
    // Trial 2 mm screw scheme: 2.4 clearance in cradle, 1.8 blind pilot in posts.
    // Fastener type/length and pilot fit must be selected and tested before use.
    var bodies=[roof];
    for(var side in [-1,1])
    {
        var post=prism(context,id+("post"~side),cx+side*mountX-2,cy-2.5,S,4,5,Z-S+0.1);
        cut(context,id+("pilotCut"~side),post,cylinder(context,id+("pilot"~side),cx+side*mountX,cy,S-0.1,0.9,Z-S-0.4));
        bodies=append(bodies,post);
    }
    opBoolean(context,id+"join",{"tools":qUnion(bodies),"operationType":BooleanOperationType.UNION});
    return roof;
}
function cradle(context is Context,id is Id,cx,cy,S,px,py,plateW,plateD,mountX,wireD,kind is string) returns Query
{
    // Housing bears on the upper 1.6 mm seat, not on soldered wires.
    // Pin holes are separate from a round exit in the lower wire plate.
    var seat=prism(context,id+"seat",cx-plateW/2,cy-plateD/2,S-1.6,plateW,plateD,1.6);
    // Extra encoder Y stock avoids tangency at the outermost trial pin relief.
    var wallY=2;
    if(kind=="encoder")
        wallY=2.3;
    var wall=prism(context,id+"wall",cx-px/2-2,cy-py/2-wallY,S-0.1,px+4,py+2*wallY,3.1);
    cut(context,id+"pocketCut",wall,prism(context,id+"pocket",cx-px/2,cy-py/2,S-0.2,px,py,3.4));
    var wirePlate=prism(context,id+"wirePlate",cx-plateW/2,cy-plateD/2,S-9.6,plateW,plateD,1.6);
    cut(context,id+"wireCut",wirePlate,cylinder(context,id+"wire",cx,cy,S-9.7,wireD/2,1.8));
    var bodies=[seat,wall,wirePlate];
    for(var side in [-1,1])
        bodies=append(bodies,prism(context,id+("bridge"~side),cx+side*mountX-2,cy-3,S-8.1,4,6,6.6));
    opBoolean(context,id+"join",{"tools":qUnion(bodies),"operationType":BooleanOperationType.UNION});
    for(var side in [-1,1])
        cut(context,id+("screwCut"~side),seat,cylinder(context,id+("screw"~side),cx+side*mountX,cy,S-9.7,1.2,9.8));
    var points=[];
    var pinR=0.8;
    // Drawing board patterns used as trial relief patterns; registration/orientation
    // to actual housings and printed clearance still need physical confirmation.
    if(kind=="ptt")
    {
        points=[[-2.55,-2.5],[2.55,-2.5],[-2.55,2.5],[2.55,2.5],[-2.85,0],[2.85,0]];
        pinR=0.9;
    }
    else if(kind=="power")
        points=[[-2.25,-3.25],[2.25,-3.25],[-2.25,3.25],[2.25,3.25],[-2.7,0],[2.7,0]];
    else if(kind=="encoder")
    {
        points=[[-2.5,7],[2.5,7],[-2.5,-7.5],[0,-7.5],[2.5,-7.5]];
        for(var side in [-1,1])
            cut(context,id+("tabCut"~side),seat,prism(context,id+("tab"~side),cx+side*6.25-0.9,cy-1.45,S-1.7,1.8,2.9,4.9));
    }
    else
        points=[[-3.5,1.25],[3.5,1.25],[-2.5,-1.25],[2.5,-1.25]];
    var n=0;
    for(var point in points)
    {
        var radius=pinR;
        if(kind=="reset" && n<2)
            radius=0.9;
        cut(context,id+("pinCut"~n),seat,cylinder(context,id+("pin"~n),cx+point[0],cy+point[1],S-1.7,radius,4.9));
        n+=1;
    }
    return seat;
}
function dSocket(context is Context,id is Id,x,y,z,clearance,depth) returns Query
{
    // Shaft nominal diameter 6, flat-to-opposite-tangent 4.5.
    // clearance is total diametral addition; the flat is offset by clearance/2.
    var r=3+clearance/2;
    var f=1.5+clearance/2;
    var h=sqrt(r*r-f*f);
    var s=newSketchOnPlane(context,id+"s",{"sketchPlane":plane(vector(x,y,z)*millimeter,vector(0,0,1))});
    skArc(s,"a",{"start":vector(f,h)*millimeter,"mid":vector(-r,0)*millimeter,"end":vector(f,-h)*millimeter});
    skLineSegment(s,"l",{"start":vector(f,-h)*millimeter,"end":vector(f,h)*millimeter});
    skSolve(s);
    opExtrude(context,id+"e",{"entities":qSketchRegion(id+"s"),"direction":vector(0,0,1),"endBound":BoundingType.BLIND,"endDepth":depth*millimeter});
    opDeleteBodies(context,id+"ds",{"entities":qCreatedBy(id+"s",EntityType.BODY)});
    return qCreatedBy(id+"e",EntityType.BODY);
}

annotation { "Feature Type Name" : "SWS enclosure prototype" }
export const swsPrototype = defineFeature(function(context is Context,id is Id,definition is map)
    precondition
    {
        annotation { "Name" : "Base underside to lid underside" }
        isLength(definition.height,HEIGHT);
        annotation { "Name" : "Knob diameter" }
        isLength(definition.knobDiameter,KNOB_D);
        annotation { "Name" : "Knob socket diametral allowance" }
        isLength(definition.fit,FIT);
        annotation { "Name" : "Lid display offset (0 = assembled)" }
        isLength(definition.lidOffset,LID_OFFSET);
        annotation { "Name" : "Show centred base fit reference", "Default" : false }
        definition.showBase is boolean;
        annotation { "Name" : "Show mounting prototypes - fit unverified", "Default" : true }
        definition.mounts is boolean;
        annotation { "Name" : "Paired speaker grilles - owner 35 x 25 footprint", "Default" : true }
        definition.speakerGrilles is boolean;
        annotation { "Name" : "Show speaker clearance envelopes - 35 x 25 x 6.2", "Default" : false }
        definition.showSpeakers is boolean;
        annotation { "Name" : "Speaker support shelves - trial fit", "Default" : true }
        definition.speakerSupports is boolean;
        annotation { "Name" : "Pi port access windows - trial plug fit", "Default" : true }
        definition.portOpenings is boolean;
        annotation { "Name" : "Pi PCB underside seat - match base posts" }
        isLength(definition.piSeat,PI_SEAT);
        annotation { "Name" : "PTT square pocket - trial housing size" }
        isLength(definition.pttPocket,PTT_POCKET);
        annotation { "Name" : "Power square pocket - trial housing size" }
        isLength(definition.powerPocket,POWER_POCKET);
        annotation { "Name" : "Encoder body pocket width - trial" }
        isLength(definition.encPocketX,ENC_POCKET_X);
        annotation { "Name" : "Encoder body pocket depth - trial" }
        isLength(definition.encPocketY,ENC_POCKET_Y);
        annotation { "Name" : "Reset pocket width - trial envelope" }
        isLength(definition.resetPocketX,RESET_POCKET_X);
        annotation { "Name" : "Reset pocket depth - trial envelope" }
        isLength(definition.resetPocketY,RESET_POCKET_Y);
        annotation { "Name" : "PTT seat below lid - prototype" }
        isLength(definition.pttSeat,PTT_SEAT);
        annotation { "Name" : "Power seat below lid - prototype" }
        isLength(definition.powerSeat,POWER_SEAT);
        annotation { "Name" : "Encoder seat below lid - prototype" }
        isLength(definition.encSeat,ENC_SEAT);
        annotation { "Name" : "Reset seat below lid - actual H unknown" }
        isLength(definition.resetSeat,RESET_SEAT);
        annotation { "Name" : "Spare reset guide-to-seat drop - trial" }
        isLength(definition.resetTestSeat,RESET_TEST_SEAT);
        annotation { "Name" : "Round wire exits - verify bundle size" }
        isLength(definition.wirePort,WIRE_PORT);
    }
    {
        var H=definition.height/millimeter;
        // Inspected 90.5 x 58.4 R2 base + 0.2 per side CAD clearance.
        // Outer sleeve = 94.9 x 62.8; wall = 2. Lid shown exploded by 10.
        var shell=roundedPrism(context,id+"shell",-47.45,-31.4,0,94.9,62.8,H,4.2);
        var cavity=roundedPrism(context,id+"cavity",-45.45,-29.4,-1,90.9,58.8,H+2,2.2);
        cut(context,id+"hollow",shell,cavity);
        if(definition.portOpenings)
        {
            // Official Pi5 STEP lower PCB face z.03 seated on existing posts z7.
            // XY translation(-42.5,-28); default Z translation6.97.
            // Source: https://pip.raspberrypi.com/categories/892-raspberry-pi-5
            var dz=definition.piSeat/millimeter-7;
            wallWindow(context,id+"usbLower",shell,"right",1,16.69+dz,16.5,18);
            wallWindow(context,id+"usbUpper",shell,"right",19,16.69+dz,16.5,18);
            wallWindow(context,id+"ethernet",shell,"right",-17.75,14.96+dz,17.6,15);
            wallWindow(context,id+"usbC",shell,"front",-31.3,10+dz,12,8);
            // Combined dual-HDMI window avoids a narrow web between plug mouldings.
            wallWindow(context,id+"hdmiPair",shell,"front",-10,10+dz,26,8);
            // Shared microSD/onboard-power service access on the left edge.
            wallWindow(context,id+"leftService",shell,"left",-1.5,9+dz,23,10);
        }
        if(definition.speakerGrilles && definition.speakerSupports)
        {
            for(var side in [-1,1])
                shell=speakerShelf(context,id+("speakerShelf"~side),shell,side*23.5,H);
        }
        namePart(context,shell,"SWS sleeve - speaker shelves and trial Pi ports - base retention pending");
        var Z=H+definition.lidOffset/millimeter;
        var lid=roundedPrism(context,id+"lid",-47.45,-31.4,Z,94.9,62.8,2,4.2);
        // Top exterior perimeter only; preserve the underside seating face and openings.
        // API: https://cad.onshape.com/FsDoc/library.html#opFillet-Context-Id-map
        opFillet(context,id+"lidTopRound",{"entities":qCapEntity(id+"lid"+"e",CapType.END,EntityType.EDGE),"radius":0.6*millimeter});
        var lip=roundedPrism(context,id+"lip",-45.15,-29.1,Z-3,90.3,58.2,3.1,1.9);
        var lipVoid=roundedPrism(context,id+"lipVoid",-43.65,-27.6,Z-3.1,87.3,55.2,3.3,0.4);
        cut(context,id+"lipCut",lip,lipVoid);
        opBoolean(context,id+"joinLip",{"tools":qUnion([lid,lip]),"operationType":BooleanOperationType.UNION});
        // Owner layout: vents above controls (+Y); encoder left, PTT centre, power right.
        // Proposed panel apertures: whole caps exposed; not panel-mount switches.
        cut(context,id+"pttCut",lid,prism(context,id+"ptt",-6.4,-18.4,Z-0.1,12.8,12.8,2.2));
        cut(context,id+"encoderCut",lid,cylinder(context,id+"encoder",-28,-12,Z-0.1,3.25,2.2));
        cut(context,id+"powerCut",lid,cylinder(context,id+"power",28,-10,Z-0.1,5.2,2.2));
        // Proposed printed-plunger guide below power; not a manufacturer panel cutout.
        // 6 mm stem in 6.6 mm opening. Actual TS365ZJ height/support remain unresolved.
        cut(context,id+"resetCut",lid,cylinder(context,id+"reset",28,-22,Z-0.1,3.3,2.2));
        var speakerEnvelopes=[];
        var speakerInfo="Original nine vents; speaker grilles hidden. ";
        if(definition.speakerGrilles)
        {
            // Owner-supplied housing envelope 35 x 25 x 6.2 mm, not measured here.
            // Slots are a trial acoustic grille layout, not a housing-through cutout.
            // Actual outlet position/retention/fasteners and thermal behavior remain open.
            for(var side in [-1,1])
            {
                var cx=side*23.5;
                for(var row=0;row<5;row+=1)
                {
                    var grilleId=id+("speaker"~side~"row"~row);
                    cut(context,grilleId+"cut",lid,roundedPrism(context,grilleId,cx-13.5,4.3+row*4,Z-0.1,27,2.4,2.2,1));
                }
                // Speakers stay on fixed sleeve shelves when the lid is shown exploded.
                speakerEnvelopes=append(speakerEnvelopes,prism(context,id+("speakerEnvelope"~side),cx-17.5,1,H-6.6,35,25,6.2));
            }
            // Free central vents are outside the speaker footprint; acoustic slots
            // covered by speaker boxes must not be counted as free cooling vents.
            for(var side in [-1,1])
            {
                var ventId=id+("centreVent"~side);
                cut(context,ventId+"cut",lid,roundedPrism(context,ventId,side*3-1.5,7,Z-0.1,3,16,2.2,1));
            }
            speakerInfo="Speaker envelopes checked at .4 mm face gap; shelves/+X wire relief and Pi windows are trial fits; electronics/strength/thermal fit unverified. ";
        }
        else
        {
            for(var i=0;i<9;i+=1)
                cut(context,id+("ventCut"~i),lid,prism(context,id+("vent"~i),-33+i*8,7,Z-0.1,3,16,2.2));
        }
        var carriers=[];
        var supportGap="Mounts hidden.";
        if(definition.mounts)
        {
            var wireD=definition.wirePort/millimeter;
            var S=Z-definition.pttSeat/millimeter;
            var carrier=cradle(context,id+"pttCradle",0,-12,S,definition.pttPocket/millimeter,definition.pttPocket/millimeter,26,16,10,wireD,"ptt");
            lid=mountingPosts(context,id+"pttMount",lid,0,-12,Z,S,10);
            namePart(context,carrier,"PTT cradle - trial square pocket - housing fit/retention unverified");
            carriers=append(carriers,carrier);
            S=Z-definition.encSeat/millimeter;
            carrier=cradle(context,id+"encCradle",-28,-12,S,definition.encPocketX/millimeter,definition.encPocketY/millimeter,28,24,11,wireD,"encoder");
            lid=mountingPosts(context,id+"encMount",lid,-28,-12,Z,S,11);
            namePart(context,carrier,"Encoder cradle - trial body pocket and tab relief - fit unverified");
            carriers=append(carriers,carrier);
            S=Z-definition.powerSeat/millimeter;
            carrier=cradle(context,id+"powerCradle",28,-10,S,definition.powerPocket/millimeter,definition.powerPocket/millimeter,24,14,9,wireD,"power");
            lid=mountingPosts(context,id+"powerMount",lid,28,-10,Z,S,9);
            namePart(context,carrier,"Power cradle - trial square pocket - housing fit/retention unverified");
            var powerCarrier=carrier;
            carriers=append(carriers,carrier);
            S=Z-definition.resetSeat/millimeter;
            carrier=cradle(context,id+"resetCradle",28,-22,S,definition.resetPocketX/millimeter,definition.resetPocketY/millimeter,24,9,9.5,wireD,"reset");
            lid=mountingPosts(context,id+"resetMount",lid,28,-22,Z,S,9.5);
            namePart(context,carrier,"Reset A cradle - trial seat - actual switch H/retention unresolved");
            carriers=append(carriers,carrier);
            checkNoInterference(context,qUnion(carriers),qUnion([shell,lid]),"Cradles versus sleeve/lid posts");
            for(var a=0;a<size(carriers);a+=1)
                for(var b=a+1;b<size(carriers);b+=1)
                    checkNoInterference(context,carriers[a],carriers[b],"Adjacent cradles");
            var carrierGap=evDistance(context,{"side0":powerCarrier,"side1":carrier}).distance/millimeter;
            supportGap="Cradle checks: no solid interference; power/reset minimum gap " ~ carrierGap ~ " mm.";
        }
        var mountLabel="hidden";
        if(definition.mounts)
            mountLabel="shown";
        namePart(context,lid,"SWS lid - offset " ~ (definition.lidOffset/millimeter) ~ " mm - prototype mounts " ~ mountLabel);
        if(size(speakerEnvelopes)>0)
        {
            checkNoInterference(context,qUnion(speakerEnvelopes),qUnion(append(carriers,qUnion([shell,lid]))),"Speaker envelopes versus sleeve/lid/cradles");
            checkNoInterference(context,speakerEnvelopes[0],speakerEnvelopes[1],"Left/right speaker envelopes");
        }
        // Centred CAD reference reconstructed from the inspected Feature Studio 2.
        // Original/corrected base studios are not modified or imported by this check.
        var base=roundedPrism(context,id+"fitBase",-45.25,-29.2,0,90.5,58.4,2,2);
        var postBodies=[base];
        for(var bx=0;bx<2;bx+=1)
            for(var by=0;by<2;by+=1)
                postBodies=append(postBodies,cylinder(context,id+("fitPost"~bx~by),-39+bx*58,-24.5+by*49,2,1.25,5));
        opBoolean(context,id+"fitJoin",{"tools":qUnion(postBodies),"operationType":BooleanOperationType.UNION});
        var fitTargets=append(carriers,qUnion([shell,lid]));
        if(size(speakerEnvelopes)>0)
            fitTargets=append(fitTargets,qUnion(speakerEnvelopes));
        var clashes=evCollision(context,{"tools":base,"targets":qUnion(fitTargets)});
        for(var clash in clashes)
            if(clash["type"]!=ClashType.NONE)
                throw regenError("Base fit reference collides with sleeve, lid, cradles or speaker envelopes.");
        var gap=evDistance(context,{"side0":base,"side1":shell}).distance/millimeter;
        if(gap<0.199)
            throw regenError("Base-to-sleeve CAD gap is below the intended 0.2 mm.");
        reportFeatureInfo(context,id,speakerInfo ~ "Base CAD check: no collision; minimum sleeve gap "~gap~" mm. " ~ supportGap ~ " Printed fit and retention remain unverified.");
        if(size(speakerEnvelopes)>0)
        {
            if(definition.showSpeakers)
            {
                namePart(context,speakerEnvelopes[0],"Left speaker clearance envelope - owner 35 x 25 x 6.2 - mounting unverified");
                namePart(context,speakerEnvelopes[1],"Right speaker clearance envelope - owner 35 x 25 x 6.2 - mounting unverified");
            }
            else
                opDeleteBodies(context,id+"removeSpeakerEnvelopes",{"entities":qUnion(speakerEnvelopes)});
        }
        if(definition.showBase)
            namePart(context,base,"Base fit reference - centred - CAD only");
        else
            opDeleteBodies(context,id+"removeFitBase",{"entities":base});
        var R=definition.knobDiameter/millimeter/2;
        var knob=cylinder(context,id+"knob",70,0,0,R,14);
        cut(context,id+"socketCut",knob,dSocket(context,id+"socket",70,0,-0.1,definition.fit/millimeter,9.1));
        for(var j=0;j<16;j+=1)
        {
            var a=j*360/16*degree;
            cut(context,id+("gripCut"~j),knob,cylinder(context,id+("grip"~j),70+(R+0.6)*cos(a),(R+0.6)*sin(a),-0.1,1.1,14.2));
        }
        namePart(context,knob,"EC11 D-shaft knob - " ~ (definition.knobDiameter/millimeter) ~ " x 14 nominal - fit test required");
        // Separate solid reset-cap prototype shown seated: flange 8.5 x 1, stem 6 x 3.1.
        // Flange top at lid underside; cap projects 1 mm above the lid.
        // Trial carrier below it; actual switch H/contact and retention remain open.
        var resetCap=cylinder(context,id+"resetCapFlange",28,-22,Z-1,4.25,1);
        var resetStem=cylinder(context,id+"resetCapStem",28,-22,Z-0.1,3,3.1);
        opFillet(context,id+"resetCapTopRound",{"entities":qCapEntity(id+"resetCapStem"+"e",CapType.END,EntityType.EDGE),"radius":0.5*millimeter});
        opBoolean(context,id+"resetCapJoin",{"tools":qUnion([resetCap,resetStem]),"operationType":BooleanOperationType.UNION});
        namePart(context,resetCap,"Reset plunger cap - 6 mm stem - switch height/support pending");
        // Independent reset B module: recessed tool access, no plunger.
        // Two distinct solids, neither joined to the enclosure or reset A cap.
        var guide=roundedPrism(context,id+"spareGuide",92,-8,20,24,16,2,2);
        cut(context,id+"spareAccessCut",guide,cylinder(context,id+"spareAccess",104,0,19.9,2,2.2));
        var spareS=20-definition.resetTestSeat/millimeter;
        var spare=cradle(context,id+"spareCradle",104,0,spareS,definition.resetPocketX/millimeter,definition.resetPocketY/millimeter,24,9,9.5,definition.wirePort/millimeter,"reset");
        guide=mountingPosts(context,id+"spareMount",guide,104,0,20,spareS,9.5);
        checkNoInterference(context,spare,guide,"Spare reset B cradle/guide");
        namePart(context,guide,"Spare reset B - recessed 4 mm access guide - separate test module");
        namePart(context,spare,"Spare reset B cradle - trial pocket and round wire exit - fit unverified");
        // Coupon: three D-bores in left-to-right order, 6.1/6.2/6.3 diameters.
        var coupon=prism(context,id+"coupon",54,-30,0,32,12,4);
        for(var k=0;k<3;k+=1)
        {
            cut(context,id+("couponCut"~k),coupon,dSocket(context,id+("couponBore"~k),60+k*10,-24,-0.1,0.1+k*0.1,4.2));
        }
        namePart(context,coupon,"D-shaft fit coupon - left to right 6.1 6.2 6.3 mm");
    });
