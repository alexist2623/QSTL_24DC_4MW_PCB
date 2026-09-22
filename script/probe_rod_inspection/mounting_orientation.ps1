# Keep the confirmed device reversal, with the boss pointing inward between rods.
function Multiply-Placement($left,$right,$geometry) {
    $result=$geometry.CreateMatrix()
    for($i=1;$i -le 4;$i++) {for($j=1;$j -le 4;$j++) {
        $value=0.0;for($k=1;$k -le 4;$k++) {$value+=$left.Cell($i,$k)*$right.Cell($k,$j)}
        $result.Cell($i,$j)=$value
    }}
    return $result
}
function Save-MountingPlacements($assembly,$directory) {
    $records=@()
    foreach($occ in $assembly.ComponentDefinition.Occurrences) {
        $matrix=@();for($i=1;$i -le 4;$i++) {$row=@();for($j=1;$j -le 4;$j++) {$row+=$occ.Transformation.Cell($i,$j)};$matrix+=,$row}
        $records+=[pscustomobject]@{name=$occ.Name;matrix_cm=$matrix;path=$occ.Definition.Document.FullFileName}
    }
    $records|ConvertTo-Json -Depth 8|Set-Content -LiteralPath (Join-Path $directory 'inward_placements.json') -Encoding UTF8
}
function Apply-ConfirmedMountingOrientation($assembly,$geometry) {
    $device=$geometry.CreateMatrix();$device.SetToRotation([Math]::PI,$geometry.CreateVector(0,0,1),$geometry.CreatePoint(0,0,0))
    $device.SetTranslation($geometry.CreateVector(5.1,35.365604733031688,0),$false)
    $inward=$geometry.CreateMatrix();$inward.SetTranslation($geometry.CreateVector(0,0,-1),$false)
    foreach($occ in $assembly.ComponentDefinition.Occurrences) {
        $m=$geometry.CreateMatrix();$move=$true
        if ($occ.Name -eq 'Solid_Plate_With_Integral_Mounting_Boss') {
            $m.SetTranslation($geometry.CreateVector(0,13.5,-0.4),$false)
        } elseif ($occ.Name -eq 'Existing_Carrier_Hung_From_Side_Slots') {
            $m.SetToRotation([Math]::PI,$geometry.CreateVector(0,1,0),$geometry.CreatePoint(0,0,0))
            $m.SetTranslation($geometry.CreateVector(4.196412701191219,13.070466430122147,2.418839662),$false)
            $m=Multiply-Placement $device $m $geometry;$m=Multiply-Placement $inward $m $geometry
        } elseif ($occ.Name -match '^Device_Clamp_M3_([12])$') {
            $y=17.682802366515844+1.6*([int]$Matches[1]-1)
            $m.SetToRotation((-[Math]::PI/2),$geometry.CreateVector(0,1,0),$geometry.CreatePoint(0,0,0))
            $m.SetTranslation($geometry.CreateVector(3.4245592247731516,$y,1.3),$false)
            $m=Multiply-Placement $device $m $geometry;$m=Multiply-Placement $inward $m $geometry
        } elseif ($occ.Name -match '^Rod_Clamp_M3_X(3|48)_Y([0-9]+)$') {
            $m.SetTranslation($geometry.CreateVector(([double]$Matches[1]/10),([double]$Matches[2]/10),-0.4),$false)
        } else {$move=$false}
        if ($move) {$occ.Grounded=$false;$occ.Transformation=$m;$occ.Grounded=$true}
    }
}
