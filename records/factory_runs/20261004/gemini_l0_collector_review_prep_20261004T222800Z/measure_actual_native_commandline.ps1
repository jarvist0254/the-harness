function Measure-ActualNativeCommandLine([Diagnostics.ProcessStartInfo]$StartInfo){
 $flags=[Reflection.BindingFlags]'NonPublic,Static'
 $methods=@([Diagnostics.Process].GetMethods($flags)|Where-Object Name -ceq 'BuildCommandLine')
 if($methods.Count-ne1){throw 'actual.NET commandline method unavailable'}
 $method=$methods[0];$parameters=$method.GetParameters()
 if($parameters.Count-ne2-or$parameters[0].ParameterType-ne[Diagnostics.ProcessStartInfo]-or!$parameters[1].ParameterType.IsByRef){throw 'actual.NET commandline signature drift'}
 $builderType=$parameters[1].ParameterType.GetElementType()
 $toString=$builderType.GetMethod('ToString',[Reflection.BindingFlags]'Public,Instance',$null,[type[]]@(),$null)
 if(!$toString-or$toString.ReturnType-ne[string]){throw 'actual.NET builder ToString unavailable'}
 $dm=[Reflection.Emit.DynamicMethod]::new('ReadOnlyMeasureProcessCommandLine',[string],[type[]]@([Diagnostics.ProcessStartInfo]),[Diagnostics.Process],$true)
 $il=$dm.GetILGenerator();$local=$il.DeclareLocal($builderType)
 $il.Emit([Reflection.Emit.OpCodes]::Ldloca,$local);$il.Emit([Reflection.Emit.OpCodes]::Initobj,$builderType)
 $il.Emit([Reflection.Emit.OpCodes]::Ldarg_0);$il.Emit([Reflection.Emit.OpCodes]::Ldloca,$local);$il.Emit([Reflection.Emit.OpCodes]::Call,$method)
 $il.Emit([Reflection.Emit.OpCodes]::Ldloca,$local);$il.Emit([Reflection.Emit.OpCodes]::Call,$toString);$il.Emit([Reflection.Emit.OpCodes]::Ret)
 $fn=$dm.CreateDelegate([Func[Diagnostics.ProcessStartInfo,string]])
 $line=$fn.Invoke($StartInfo)
 return @{utf16_code_units=$line.Length;including_terminating_nul_utf16_code_units=($line.Length+1);method='Actual installed .NET Process.BuildCommandLine via managed Reflection.Emit; no Process.Start/native call';dotnet_runtime=[Runtime.InteropServices.RuntimeInformation]::FrameworkDescription;process_started=$false;native_calls=0}
}
