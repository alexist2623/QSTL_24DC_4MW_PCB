$ErrorActionPreference='Stop'
Add-Type -Path 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll'
Add-Type -ReferencedAssemblies 'C:\Program Files\Autodesk\Inventor 2027\Bin\Public Assemblies\Autodesk.Inventor.Interop.dll' -TypeDefinition @'
public static class DrawingBridge {
 public static object EditTitle(object obj) {
  var d = (Inventor.TitleBlockDefinition)obj;
  Inventor.DrawingSketch s; d.Edit(out s); return s;
 }
}
'@
$root='C:\JeonghyunPark\Workspace\QSTL_24DC_4MW_PCB'
$here=Join-Path $root 'script\support_flange_1p6mm_20260924'
$model=Join-Path $root 'QSTL_24DC_4MW_PCB\Mechanical_Assembly\Rod_Holder_Adapter_Drop8p5'
$out=Join-Path $model 'Manufacturing_DWG'
$null=New-Item -ItemType Directory -Path $out -Force
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('Inventor.Application')
$tg=$app.TransientGeometry;$to=$app.TransientObjects
$oldSilent=$app.SilentOperation;$app.SilentOperation=$true
$audit=[Collections.Generic.List[object]]::new()
$modelFiles=@('Centre_Plate.ipt','Left_Rod_Support.ipt','Right_Rod_Support.ipt','Rod_Holder_Assembly_Drop8p5.iam')
$hashes=@{};foreach($f in $modelFiles){$hashes[$f]=(Get-FileHash -LiteralPath (Join-Path $model $f)).Hash}
function P2($x,$y){return $tg.CreatePoint2d($x/10.0,$y/10.0)}
function P3($p){return $tg.CreatePoint($p[0]/10.0,$p[1]/10.0,$p[2]/10.0)}
function Note($x,$y,$value,$height=2.5){
 $safe=[Security.SecurityElement]::Escape([string]$value)
 $null=$script:sheet.DrawingNotes.GeneralNotes.AddFitted((P2 $x $y),('<StyleOverride Font="Arial" FontSize="'+($height/10).ToString([Globalization.CultureInfo]::InvariantCulture)+'">'+$safe+'</StyleOverride>'))
}
function Lines($segments){
 $sk=$script:sheet.Sketches.Add();$sk.Edit()
 foreach($q in $segments){$null=$sk.SketchLines.AddByTwoPoints((P2 $q[0] $q[1]),(P2 $q[2] $q[3]))}
 $sk.ExitEdit();return $sk
}
function Frame($code,$title,$number,$scale,$material='OXYGEN-FREE COPPER'){
 $s=$script:sheet
 if($s.TitleBlock){$s.TitleBlock.Delete()};if($s.Border){$s.Border.Delete()}
 $s.Size=[Inventor.DrawingSheetSizeEnum]::kA3DrawingSheetSize
 $s.Orientation=[Inventor.PageOrientationTypeEnum]::kLandscapePageOrientation
 $s.Name=$code
 $null=$s.AddDefaultBorder()
 $definition=$doc.TitleBlockDefinitions.Add('QSTL '+$code)
 $sk=[DrawingBridge]::EditTitle($definition)
 $segments=@(@(0,0,185,0),@(185,0,185,36),@(185,36,0,36),@(0,36,0,0),@(0,9,185,9),@(0,21,185,21),@(60,0,60,36),@(143,0,143,21),@(165,0,165,9))
 foreach($q in $segments){$null=$sk.SketchLines.AddByTwoPoints((P2 $q[0] $q[1]),(P2 $q[2] $q[3]))}
 function TB($x,$y,$text,$size=2.5){
  $safe=[Security.SecurityElement]::Escape($text)
  $null=$sk.TextBoxes.AddFitted((P2 $x $y),('<StyleOverride Font="Arial" FontSize="'+($size/10).ToString([Globalization.CultureInfo]::InvariantCulture)+'">'+$safe+'</StyleOverride>'))
 }
 TB 3 33 'QSTL' 4;TB 3 26 'DIMENSIONS IN mm' 2.4
 TB 63 33 $title 3.5;TB 63 26 $code 3
 TB 3 18 'MATERIAL' 1.8;TB 3 14 $material 2.2
 TB 63 18 'SURFACE TREATMENT' 1.8;TB 63 14 'NONE' 2.5
 TB 146 18 'DATE' 1.8;TB 146 14 '2026-09-24' 2.3
 TB 3 6 'THIRD ANGLE PROJECTION' 2.2
 TB 63 6 ('SCALE: '+$scale) 2.2
 TB 146 6 'REV D' 2.2;TB 168 6 ($number.ToString()+' / 5') 2.2
 $definition.ExitEdit($true)
 $null=$s.AddTitleBlock($definition,[Inventor.TitleBlockLocationEnum]::kBottomRightPosition)
}
function View($file,$x,$y,$scale,$normal,$up,$name,$hidden=$false){
 $part=$app.Documents.Open((Join-Path $model $file),$false)
 $cam=$to.CreateCamera();$cam.Target=$tg.CreatePoint(0,0,0)
 $cam.Eye=$tg.CreatePoint($normal[0]*100,$normal[1]*100,$normal[2]*100)
 $cam.UpVector=$tg.CreateUnitVector($up[0],$up[1],$up[2])
 $style=if($hidden){[Inventor.DrawingViewStyleEnum]::kHiddenLineDrawingViewStyle}else{[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle}
 $v=$script:sheet.DrawingViews.AddBaseView($part,(P2 $x $y),$scale,[Inventor.ViewOrientationTypeEnum]::kArbitraryViewOrientation,$style,'',$cam)
 $v.Name=$name;$v.ShowLabel=$false;$doc.Update2($false)|Out-Null
 return $v
}
function Intent($v,$coords){
 $p=$v.ModelToSheetSpace((P3 $coords));$best=$null;$bestType=$null;$distance=1e9
 foreach($c in $v.DrawingCurves()){
  foreach($kind in @('StartPoint','EndPoint','CenterPoint')){
   $q=$c.$kind;if($null -eq $q){continue}
   $d=[math]::Sqrt([math]::Pow($p.X-$q.X,2)+[math]::Pow($p.Y-$q.Y,2))
   if($d -lt $distance){$distance=$d;$best=$c;$bestType=$kind}
  }
 }
 if($distance -gt 0.001){throw "No geometry at $coords in $($v.Name); error $($distance*10) mm"}
 $enum=switch($bestType){'StartPoint'{[Inventor.PointIntentEnum]::kStartPointIntent};'EndPoint'{[Inventor.PointIntentEnum]::kEndPointIntent};'CenterPoint'{[Inventor.PointIntentEnum]::kCenterPointIntent}}
 return $script:sheet.CreateGeometryIntent($best,$enum)
}
function Dim($v,$a,$b,$axis,$x,$y,$expected,$suffix='',$digits=2){
 $ia=Intent $v $a;$ib=Intent $v $b
 $kind=if($axis -eq 'H'){[Inventor.DimensionTypeEnum]::kHorizontalDimensionType}else{[Inventor.DimensionTypeEnum]::kVerticalDimensionType}
 $d=$script:sheet.DrawingDimensions.GeneralDimensions.AddLinear((P2 $x $y),$ia,$ib,$kind,$true,$script:ds)
 $d.Precision=$digits
 if($suffix){$d.Text.FormattedText='<DimensionValue/>'+[Security.SecurityElement]::Escape($suffix)}
 $val=$d.ModelValue*10
 if([math]::Abs($val-$expected)-gt 0.0001){throw "Dimension differs: expected $expected, actual $val on $($sheet.Name)"}
 $audit.Add([ordered]@{sheet=$sheet.Name;view=$v.Name;expected_mm=$expected;native_model_value_mm=$val;displayed_text=$d.Text.Text;precision=$d.Precision})
 return $d
}
function Lead($v,$coords,$x,$y,$value){
 $points=$to.CreateObjectCollection();$points.Add((P2 $x $y));$points.Add((Intent $v $coords))
 $safe=[Security.SecurityElement]::Escape($value)
 $null=$script:sheet.DrawingNotes.LeaderNotes.Add($points,('<StyleOverride Font="Arial" FontSize="0.25">'+$safe+'</StyleOverride>'))
}
function Marks($v){
 $seen=@{}
 foreach($c in $v.DrawingCurves()){
  if($c.CurveType -ne [Inventor.CurveTypeEnum]::kCircleCurve -or !$c.CenterPoint){continue}
  $p=$c.CenterPoint;$key=('{0:F5}/{1:F5}' -f $p.X,$p.Y)
  if(!$seen.ContainsKey($key)){$null=$script:sheet.Centermarks.Add($script:sheet.CreateGeometryIntent($c),$true,$true);$seen[$key]=$true}
 }
}
function Section($parent,$a,$b,$x,$y,$scale,$name){
 $sk=$parent.Sketches.Add();$sk.Edit()
 $pa=$sk.SheetToSketchSpace($parent.ModelToSheetSpace((P3 $a)));$pb=$sk.SheetToSketchSpace($parent.ModelToSheetSpace((P3 $b)))
 $null=$sk.SketchLines.AddByTwoPoints($pa,$pb);$sk.ExitEdit()
 $v=$script:sheet.DrawingViews.AddSectionView($parent,$sk,(P2 $x $y),[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle,$scale,$true,$name,$true,$false,'0.01 mm')
 $v.Aligned=$false;$v.Position=P2 $x $y;$doc.Update2($false)|Out-Null
 $v.Label.FormattedText='<StyleOverride Font="Arial" FontSize="0.3">SECTION '+$name+'-'+$name+"`nSCALE "+$scale+':1</StyleOverride>'
 $v.Label.Position=P2 $x ($y-$v.Height*5-8)
 # Replace template cross-sheet identifier placeholders with clean same-sheet cut marks.
 $v.DisplayDefinitionInBase=$false
 $qa=$parent.ModelToSheetSpace((P3 $a));$qb=$parent.ModelToSheetSpace((P3 $b))
 $xa=$qa.X*10;$xb=$qb.X*10;$yy=$qa.Y*10;$dir=if($y -gt $parent.Position.Y*10){-1}else{1}
 $segments=@();for($xx=$xa;$xx -lt $xb;$xx+=4){$segments+=,@($xx,$yy,[math]::Min($xx+3,$xb),$yy)}
 foreach($xx in @($xa,$xb)){
  $tip=$yy+$dir*7
  $segments+=,@($xx,$yy,$xx,$tip)
  $segments+=,@(($xx-0.85),($tip-$dir*2),$xx,$tip)
  $segments+=,@(($xx+0.85),($tip-$dir*2),$xx,$tip)
  Note ($xx-4.5) ($tip+1.4) $name 3
 }
 $null=Lines $segments
 return $v
}
function NewSheet($code,$title,$n,$scale,$material='OXYGEN-FREE COPPER'){
 if($n -eq 1){$script:sheet=$doc.Sheets.Item(1)}else{$script:sheet=$doc.Sheets.Add([Inventor.DrawingSheetSizeEnum]::kA3DrawingSheetSize,[Inventor.PageOrientationTypeEnum]::kLandscapePageOrientation,$code)}
 $script:sheet.Activate();Frame $code $title $n $scale $material
}
try{
 foreach($d in @($app.Documents)){if($d.DocumentType -eq [Inventor.DocumentTypeEnum]::kDrawingDocumentObject -and ($d.FullFileName -like "$out*" -or $d.DisplayName -eq 'QSTL Split Mount - CNC and Assembly')){$d.Close($true)}}
 $doc=$app.Documents.Add([Inventor.DocumentTypeEnum]::kDrawingDocumentObject,'C:\Users\Public\Documents\Autodesk\Inventor 2027\Templates\en-US\Metric\ISO.idw',$true)
 $doc.DisplayName='QSTL Split Mount - CNC and Assembly'
 $ds=$doc.StylesManager.DimensionStyles.Item('Default (ISO)')
 $ds.TextStyle.Font='Arial';$ds.TextStyle.FontSize=0.25;$ds.LinearPrecision=[Inventor.LinearPrecisionEnum]::kTwoDecimalPlacesLinearPrecision
 $ds.DecimalMarkerType=[Inventor.DecimalMarkerTypeEnum]::kPeriodDecimalMarker
 $ds.ArrowheadSize=0.23;$ds.TrailingZeroDisplay=$true
 $doc.StylesManager.ActiveStandardStyle.FirstAngleProjection=$false
 $doc.UnitsOfMeasure.LengthUnits=[Inventor.UnitsTypeEnum]::kMillimeterLengthUnits

 # CP-01: direct model-associated overall, boss and hole-pattern dimensions.
 NewSheet 'QSTL-CP01' 'CENTRAL PLATE + BOSS' 1 '1.5:1 / ISO 1:1'
 $v=View 'Centre_Plate.ipt' 85 155 1.5 @(0,0,1) @(0,1,0) 'BOSS FACE' $false
 $end=$sheet.DrawingViews.AddProjectedView($v,(P2 85 240),[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle)
 $side=$sheet.DrawingViews.AddProjectedView($v,(P2 187 155),[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle)
 $iso=View 'Centre_Plate.ipt' 331 192 1 @(1,-1,1) @(0,1,0) 'ISOMETRIC' $false
 $doc.Update2($false)|Out-Null;Marks $v;Marks $side
 $null=Dim $v @(6,0,0) @(6,80,0) V 30 155 80
 $null=Dim $v @(17.0935352141807,4,3.5) @(17.0935352141807,76,3.5) V 22 155 72 ' (2X GROOVES)'
 $null=Dim $v @(6,0,0) @(45,0,0) H 85 72 39
 $null=Dim $v @(6,0,0) @(9.5,10,0) H 55 84 3.5
 $null=Dim $v @(9.5,10,0) @(41.5,10,0) H 86 84 32
 $null=Dim $v @(9.5,10,0) @(9.5,70,0) V 42 155 60 ' (3 X 20 PITCH)'
 $null=Dim $v @(6,0,0) @(9.5,10,0) V 50 103 10
 $null=Dim $v @(19.933375831081,4,4) @(19.933375831081,76,4) V 123 155 72
 $null=Dim $v @(45,0,4) @(33.433375831081,4,4) V 133 98 4
 $null=Dim $end @(6,0,0) @(19.933375831081,4,4) H 66 260 13.933375831081 '' 4
 $null=Dim $end @(19.933375831081,4,10) @(33.433375831081,4,10) H 93 252 13.5
 $null=Dim $end @(45,0,0) @(45,0,4) V 132 242 4
 $null=Dim $end @(33.433375831081,4,4) @(33.433375831081,4,10) V 118 234 6
 $null=Dim $side @(45,0,0) @(33.433375831081,9.828023665,7) V 216 99 9.828023665 '' 4
 $null=Dim $side @(33.433375831081,9.828023665,7) @(33.433375831081,73.828023665,7) V 229 158 64 ' (4 X 16 PITCH)'
 $null=Dim $side @(33.433375831081,4,4) @(33.433375831081,9.828023665,7) H 185 80 3
 Lead $v @(41.5,70,0) 133 222 "8X Ø3.40 THRU`nØ6.60 X 90° CSK FROM OUTER FACE`nSEE CP02, SECTION B-B"
 Lead $side @(33.433375831081,73.828023665,7) 222 237 "5X M3 X 0.5 - 6H, DEPTH 6.00`nEACH SIDE (10 TOTAL); Ø2.50 PILOT`nSEE CP02, SECTION A-A"
 Note 63 65 'BOSS FACE' 2.5;Note 168 66 'RIGHT SIDE' 2.5;Note 315 116 'ISOMETRIC' 2.5
 Lead $iso @(36.7732164479817,4.5,4) 265 95 "2X DEVICE LIP RELIEF`n3.340 WIDE X 0.50 DEEP; R0.50 CORNERS`nSEE CP02, SECTION B-B"
 Write-Output 'Created central plate overall drawing.'

 # CP-02: native sections at actual threaded and countersunk hole rows.
 NewSheet 'QSTL-CP02' 'CENTRAL PLATE - DETAILS' 2 '1:1 / SECTIONS 4:1'
 $base=View 'Centre_Plate.ipt' 65 170 1 @(0,0,1) @(0,1,0) 'SECTION LOCATIONS' $false
 $sa=Section $base @(2,9.828023665,0) @(49,9.828023665,0) 264 209 4 'A'
 $sb=Section $base @(2,30,0) @(49,30,0) 264 125 4 'B'
 $doc.Update2($false)|Out-Null
 $null=Dim $sa @(19.933375831081,9.828023665,8.25) @(25.933375831081,9.828023665,8.25) H 245 248 6
 $null=Dim $sa @(27.433375831081,9.828023665,8.25) @(33.433375831081,9.828023665,8.25) H 287 248 6
 $null=Dim $sa @(25.933375831081,9.828023665,8.25) @(27.433375831081,9.828023665,8.25) H 270 237 1.5 ' WEB'
 $null=Dim $sb @(6,30,0) @(6,30,4) V 174 124 4
 $null=Dim $sb @(16.5935352141807,30,3.5) @(19.9333758310812,30,3.5) H 236 95 3.339840616900516 ' (2X)' 3
 $null=Dim $sb @(36.7732164479817,30,3.5) @(36.7732164479817,30,4) V 330 107 .5 ' (2X)'
 Lead $sb @(6.2,30,0) 157 163 "8X Ø6.60 X 90° CSK`nDEPTH 1.60 REF"
 Note 33 119 'BOSS FACE / CUT LOCATIONS' 2.5
 Note 23 102 'SECTIONS CUT THROUGH ACTUAL HOLE AXES.' 2.4
 Note 23 97 'A-A: Y=9.8280. B-B: Y=30.0000 mm.' 2.4
 Note 165 79 'BLIND THREADS: Ø2.50 FLAT-BOTTOM PILOT; NOMINAL BORE AND THREAD DEPTH 6.00.' 2.4
 Write-Output 'Created native section details.'

 # LS / RS: independent drawings with non-interchangeable coordinate patterns.
 foreach($hand in @('Left','Right')){
  $isLeft=$hand -eq 'Left';$n=if($isLeft){3}else{4};$code=if($isLeft){'QSTL-LS01'}else{'QSTL-RS01'}
  $file=$hand+'_Rod_Support.ipt';$ox=if($isLeft){0.0}else{39.0};$cx=if($isLeft){3.0}else{48.0};$tx=if($isLeft){9.5}else{41.5}
  $wx=if($isLeft){6.0}else{45.0}
  NewSheet $code ($hand.ToUpper()+' ROD SUPPORT') $n '2:1 / ISO 1.5:1'
  $v=View $file 85 153 2 @(0,0,1) @(0,1,0) 'ROD CONTACT FACE' $true
  $end=$sheet.DrawingViews.AddProjectedView($v,(P2 85 245),[Inventor.DrawingViewStyleEnum]::kHiddenLineDrawingViewStyle)
  $opp=View $file 202 153 2 @(0,0,-1) @(0,1,0) 'DECK JOINT FACE' $false
  $iso=View $file 343 203 1.5 @(1,-1,1) @(0,1,0) 'ISOMETRIC' $false
  $doc.Update2($false)|Out-Null;Marks $v;Marks $opp
  $null=Dim $v @($ox,0,12.5) @($ox,80,12.5) V 28 157 80
  $null=Dim $v @($ox,0,12.5) @(($ox+12),0,12.5) H 85 65 12
  $null=Dim $v @($cx,5,12.5) @($cx,65,12.5) V 43 151 60 ' (3 X 20 PITCH)'
  $null=Dim $v @($ox,0,12.5) @($cx,5,12.5) V 60 80 5
  $null=Dim $v @($ox,0,12.5) @($cx,5,12.5) H 81 71 ($cx-$ox)
  $null=Dim $opp @($tx,10,4) @($tx,70,4) V 168 157 60 ' (3 X 20 PITCH)'
  $null=Dim $opp @($wx,0,4) @($tx,10,4) V 181 88 10
  $null=Dim $opp @($wx,0,4) @($tx,10,4) H 199 66 ([math]::Abs($tx-$wx))
  $null=Dim $end @($wx,0,4) @($ox,0,12.5) V 128 243 8.5
  $fx=if($isLeft){0.0}else{51.0}
  $bx=if($isLeft){1.6}else{49.4}
  $null=Dim $end @($bx,0,10.9) @($fx,0,12.5) V 55 249 1.6
  Lead $end @($bx,0,10.9) 140 274 'C1.6 X 45 DEG - OUTER EDGE'
  $null=Dim $end @($wx,0,4) @($(if($isLeft){12}else{39}),0,4) H 92 259 6
  Lead $v @($cx,65,12.5) 117 219 "4X Ø3.40 THRU`nTHROUGH 1.60 FLANGE"
  Lead $opp @($tx,70,4) 230 239 "4X M3 X 0.5 - 6H`nNOMINAL DEPTH 6.50`nØ2.50 FLAT-BOTTOM PILOT`nENTRY FROM DECK JOINT FACE"
  Note 57 60 'ROD CONTACT FACE' 2.5;Note 177 60 'DECK JOINT FACE' 2.5
  Note 282 116 'CONTACT FOOTPRINT: 6.00 X 80.00' 2.5
  Note 282 109 'BLIND-HOLE BOTTOM WALL: 2.00 REF' 2.5
  Note 282 102 'LEFT / RIGHT PARTS ARE NOT INTERCHANGEABLE.' 2.3
  Write-Output ('Created '+$hand+' support drawing.')
 }

 # Native IPN explosion follows the Enclosure3 presentation workflow.
 $presentation=$app.Documents.Open((Join-Path $out 'Split_Mount_Assembly.ipn'),$false)
 $plate=$app.Documents.Open((Join-Path $out 'Split_Mount_Plate_Only.iam'),$false)
 NewSheet 'QSTL-AS01' 'PLATE ASSEMBLY' 5 'AS SHOWN' 'CP / LS / RS: OFC'
 $cam=$to.CreateCamera();$cam.Target=$tg.CreatePoint(2.55,4,-1.5);$cam.Eye=$tg.CreatePoint(30,-8,-10);$cam.UpVector=$tg.CreateUnitVector(0,1,0)
 $opts=$to.CreateNameValueMap();$opts.Add('PresentationView','View1');$opts.Add('PresentationViewAssociative',$true)
 $ev=$sheet.DrawingViews.AddBaseView($presentation,(P2 119 159),1.55,[Inventor.ViewOrientationTypeEnum]::kArbitraryViewOrientation,[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle,'View1',$cam,$opts)
 $ev.Name='EXPLODED ASSEMBLY';$ev.ShowLabel=$false
 $ev.ShowTrails=$false
 $doc.Update2($false)|Out-Null
 Note 22 278 'EXPLODED ASSEMBLY' 3.5
 Note 22 271 'SCALE 1.55:1' 2.5
 # Eight axis trails tie each fastener to its own countersink and tapped hole.
 $trail=$sheet.Sketches.Add();$trail.Edit()
 foreach($xx in @(9.5,41.5)){foreach($yy in @(10,30,50,70)){
  $p=$ev.ModelToSheetSpace((P3 @($xx,$yy,-34.9)));$q=$ev.ModelToSheetSpace((P3 @($xx,$yy,4)))
  $len=[math]::Sqrt([math]::Pow($q.X-$p.X,2)+[math]::Pow($q.Y-$p.Y,2))
  for($t=0;$t -lt $len;$t+=0.4){$a=$t/$len;$b=[math]::Min($t+0.22,$len)/$len
   $null=$trail.SketchLines.AddByTwoPoints($tg.CreatePoint2d($p.X+($q.X-$p.X)*$a,$p.Y+($q.Y-$p.Y)*$a),$tg.CreatePoint2d($p.X+($q.X-$p.X)*$b,$p.Y+($q.Y-$p.Y)*$b))
  }
 }}
 $trail.ExitEdit()
 # Short model-attached component callouts replace the removed prose blocks.
 Lead $ev @(6,0,-20) 147 70 'CP-01'
 Lead $ev @(0,0,12.5) 70 78 'LS-01'
 Lead $ev @(51,80,12.5) 24 239 'RS-01'
 Lead $ev @(41.5,70,-44.9) 151 257 "8X DIN 7991 - M3 X 10`nPITCH 0.5; 90° COUNTERSUNK"
 $cam=$to.CreateCamera();$cam.Target=$tg.CreatePoint(2.55,4,0.5);$cam.Eye=$tg.CreatePoint(12,-8,18);$cam.UpVector=$tg.CreateUnitVector(0,1,0)
 $av=$sheet.DrawingViews.AddBaseView($plate,(P2 330 204),1.25,[Inventor.ViewOrientationTypeEnum]::kArbitraryViewOrientation,[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle,'',$cam)
 $av.Name='ASSEMBLED BOSS SIDE';$av.ShowLabel=$false
 Note 282 274 'ASSEMBLED - BOSS SIDE' 3
 Note 305 266 'SCALE 1.25:1' 2.5
 $cam=$to.CreateCamera();$cam.Target=$tg.CreatePoint(0,0,0);$cam.Eye=$tg.CreatePoint(0,0,-100);$cam.UpVector=$tg.CreateUnitVector(0,1,0)
 $base=$sheet.DrawingViews.AddBaseView($plate,(P2 254 91),0.45,[Inventor.ViewOrientationTypeEnum]::kArbitraryViewOrientation,[Inventor.DrawingViewStyleEnum]::kHiddenLineRemovedDrawingViewStyle,'',$cam)
 $base.Name='JOINT SECTION LOCATION';$base.ShowLabel=$false
 $joint=Section $base @(-3,30,0) @(54,30,0) 340 102 2 'C'
 $joint.Label.Position=P2 340 138
 $null=Dim $joint @(0,30,12.5) @(51,30,12.5) H 339 76 51
 $null=Dim $joint @(6,30,4) @(51,30,12.5) V 402 105 8.5
 Note 235 63 'OUTER FACE' 2.5
 Write-Output 'Created native IPN exploded assembly, assembled isometric and fastening section.'

 $doc.Update2($false)|Out-Null;$doc.Sheets.Item(1).Activate()
 $doc.SaveAs((Join-Path $out 'QSTL_Split_Mount_RevD.idw'),$false)
 $doc.SaveAsInventorDWG((Join-Path $out 'QSTL_Split_Mount_RevD_Inventor.dwg'),$true)
 $ctx=$to.CreateTranslationContext();$ctx.Type=[Inventor.IOMechanismEnum]::kFileBrowseIOMechanism
 $add=$app.ApplicationAddIns.ItemById('{0AC6FD96-2F4D-42CE-8BE0-8AEA580399E4}')
 $opt=$to.CreateNameValueMap();$media=$to.CreateDataMedium();$null=$add.HasSaveCopyAsOptions($doc,$ctx,$opt)
 $opt.Value('All_Color_AS_Black')=1;$opt.Value('Sheet_Range')=[Inventor.PrintRangeEnum]::kPrintAllSheets;$opt.Value('Vector_Resolution')=600
 $media.FileName=Join-Path $out 'QSTL_Split_Mount_RevD.pdf';$add.SaveCopyAs($doc,$ctx,$opt,$media)
 foreach($s in $doc.Sheets){
  $code=$s.Name.Split(':')[0];$path=Join-Path $out ('QSTL_Split_Mount_RevD_'+$code+'.dwg')
  $doc.SaveAsInventorDWG($path,$true)
  $single=$app.Documents.Open($path,$true)
  foreach($other in @($single.Sheets)){if(!$other.Name.StartsWith($code+':')){$other.Delete()}}
  $single.Sheets.Item(1).Activate();$single.Update2($false)|Out-Null;$app.ActiveView.Fit();$single.Save()
  $single.Close($true)
 }
 foreach($f in $modelFiles){if((Get-FileHash -LiteralPath (Join-Path $model $f)).Hash -ne $hashes[$f]){throw "Source changed: $f"}}
 $audit|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $out 'native_dimension_audit.json')
 $hashes|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $out 'source_cad_hashes.json')
 $doc.Activate();$app.ActiveView.Fit()
 Write-Output ('Complete: '+$audit.Count+' model-associated dimensions verified; source hashes unchanged.')
}finally{$app.SilentOperation=$oldSilent}
