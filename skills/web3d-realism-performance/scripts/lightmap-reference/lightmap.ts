import * as T from 'three';
// Baked light for the lab's static surfaces (built by scripts/lightmap/: export.mjs, bake.py in Cycles, publish.py).
// Each atlas has three maps on the surfaces' second UV set: `natural` (sun and sky, bounced), `lamps` (the room's own
// lights, screens and light strips) and `ao` (occlusion within a metre, half size). The first two are irradiance with
// the surface's colour divided out, so the material's own colour and reflections still apply: a baked surface takes
// all of its diffuse light from them (the real-time lights only add highlights), and `ao` dims its reflections where
// the bake found them occluded. The manifest (src/lightmaps.json) ships with the code; a surface finds its bake by a geometry
// signature, so a mesh that has changed since the bake simply keeps real-time lighting until the next bake.

type V3=[number,number,number];
export type Signature={v:number;i:number;box:number[];probe:number[]};
type Entry={sig:Signature;atlas:number;verts:number;tris:number;src:number;index:number;uv:number};
export type Manifest={version:number;base:string;atlases:{natural:string;lamps:string;ao:string;range:{natural:number;lamps:number}}[];gain:{natural:number;lamps:number};bin:string;uvSteps:number;probe?:string|null;meshes:Entry[]};

// World-space bounds and a few sample vertices, in millimetres: equal across browsers to well within the tolerance.
export function signature(mesh:T.Mesh):Signature{
 mesh.updateWorldMatrix(true,false);
 const g=mesh.geometry,p=g.getAttribute('position'),v=new T.Vector3(),box=new T.Box3(),probe:number[]=[];
 for(let i=0;i<p.count;i++)box.expandByPoint(v.fromBufferAttribute(p,i).applyMatrix4(mesh.matrixWorld));
 for(let k=0;k<8;k++){v.fromBufferAttribute(p,Math.floor(k*(p.count-1)/7)).applyMatrix4(mesh.matrixWorld);probe.push(...(v.toArray() as V3));}
 const mm=(x:number)=>Math.round(x*1000);
 return {v:p.count,i:g.index?g.index.count:0,box:[...box.min.toArray(),...box.max.toArray()].map(mm),probe:probe.map(mm)};
}
const same=(a:Signature,b:Signature)=>a.v===b.v&&a.i===b.i&&a.box.every((x,k)=>Math.abs(x-b.box[k])<=3)&&a.probe.every((x,k)=>Math.abs(x-b.probe[k])<=3);

// The three.js geometry re-indexed for the bake: vertex j copies source vertex src[j] (a vertex on a UV seam is copied
// once per side), triangles keep their order, and `uv1` is the lightmap UV. The file stores src[j] - j and each index
// as a difference from the one before (publish.py), which compress to almost nothing.
function rebuild(g:T.BufferGeometry,entry:Entry,bin:ArrayBuffer,uvSteps:number){
 const src=new Int32Array(bin,entry.src,entry.verts).map((d,j)=>d+j),index=new Uint32Array(entry.tris*3),dIndex=new Int32Array(bin,entry.index,entry.tris*3);
 for(let k=0,v=0;k<index.length;k++)index[k]=v+=dIndex[k];
 const q=new Uint16Array(bin,entry.uv,entry.verts*2),uv=new Float32Array(q.length);for(let k=0;k<q.length;k++)uv[k]=q[k]/uvSteps;
 const out=new T.BufferGeometry();
 for(const [name,a] of Object.entries(g.attributes)){
  const n=a.itemSize,array=new (a.array.constructor as Float32ArrayConstructor)(entry.verts*n);
  for(let j=0;j<entry.verts;j++)for(let c=0;c<n;c++)array[j*n+c]=a.getComponent(src[j],c);
  out.setAttribute(name,new T.BufferAttribute(array,n,a.normalized));
 }
 out.setIndex(new T.BufferAttribute(entry.verts>65535?index:Uint16Array.from(index),1));out.setAttribute('uv1',new T.BufferAttribute(uv,2));
 out.computeBoundingSphere();out.computeBoundingBox();
 return out;
}

// Fragment changes for a baked surface: the maps are its diffuse light, and reflections are dimmed by the baked
// occlusion. Real-time lights still add their highlights (view-dependent, so not in the bake; the moon's give the
// pavilion's metal its sheen) but no diffuse light, which the maps already hold with shadows and bounces. With an
// environment map the irradiance goes through three.js's energy-conserving IBL path.
function bakedMaterial(source:T.MeshStandardMaterial,[natural,lamps,ao]:T.Texture[],range:{natural:number;lamps:number},gain:{natural:number;lamps:number}){
 const m=source.clone();m.lightMap=natural;m.lightMapIntensity=range.natural*gain.natural;
 const lampUniforms={lampMap:{value:lamps},lampIntensity:{value:range.lamps*gain.lamps},bakedAoMap:{value:ao}};
 m.onBeforeCompile=function(this:T.Material,shader:T.WebGLProgramParametersWithUniforms,renderer:T.WebGLRenderer){
  T.Material.prototype.onBeforeCompile.call(this,shader,renderer);Object.assign(shader.uniforms,lampUniforms);
  const lights='#include <lights_fragment_begin>',maps='#include <lights_fragment_maps>',end='#include <lights_fragment_end>',ao='#include <aomap_fragment>';
  if(![lights,maps,end,ao].every(k=>shader.fragmentShader.includes(k)))throw new Error('lightmap patch did not apply');
  shader.fragmentShader='uniform sampler2D lampMap,bakedAoMap;uniform float lampIntensity;\n'+shader.fragmentShader
   .replace(end,end+'\nreflectedLight.directDiffuse=vec3(0.0);')
   .replace(maps,`vec3 baked=texture2D(lightMap,vLightMapUv).rgb*lightMapIntensity+texture2D(lampMap,vLightMapUv).rgb*lampIntensity;
    #if defined( USE_ENVMAP ) && defined( STANDARD ) && defined( ENVMAP_TYPE_CUBE_UV )
     irradiance=vec3(0.0);iblIrradiance+=baked;
    #else
     irradiance=baked;
    #endif
    #if defined( USE_ENVMAP ) && defined( RE_IndirectSpecular )
     radiance+=getIBLRadiance(geometryViewDir,geometryNormal,material.roughness);
     #ifdef USE_CLEARCOAT
      clearcoatRadiance+=getIBLRadiance(geometryViewDir,geometryClearcoatNormal,material.clearcoatRoughness);
     #endif
    #endif`)
   .replace(ao,`${ao}
    #if defined( USE_ENVMAP ) && defined( STANDARD )
     reflectedLight.indirectSpecular*=computeSpecularOcclusion(saturate(dot(geometryNormal,geometryViewDir)),texture2D(bakedAoMap,vLightMapUv).r,material.roughness);
    #endif`);
 };
 m.customProgramCacheKey=()=>'baked-light';
 // For tuning tools: the unscaled ranges and the live lamp uniform (the natural map's is lightMapIntensity).
 m.userData.baked={range,lamp:lampUniforms.lampIntensity};
 return m;
}

export type Baked={count:number;missed:number;textures:T.Texture[]};
// Finds each target's bake and applies it. `half` picks the half-size atlases (touch devices). Resolves to undefined
// when there is no bake; targets without a matching entry keep real-time light.
export async function applyLightmaps(targets:T.Mesh[],manifest:Manifest,opts:{half:boolean;anisotropy:number;isDisposed:()=>boolean}):Promise<Baked|undefined>{
 if(manifest.version!==1||!manifest.atlases.length)return;
 const loader=new T.TextureLoader(),name=(file:string,half:boolean)=>manifest.base+(half?file.replace(/\.(\w+)$/,'-1k.$1'):file);
 // The maps are sRGB-encoded fractions of `range`: the GPU decodes them to linear before filtering.
 const load=async(file:string,srgb:boolean,half:boolean)=>{const t=await loader.loadAsync(name(file,half));t.channel=1;t.anisotropy=opts.anisotropy;if(srgb)t.colorSpace=T.SRGBColorSpace;return t;};
 // The UV file is gzip (publish.py); the browser inflates it.
 const inflate=(r:Response)=>{if(!r.ok||!r.body)throw new Error(`lightmap UVs: ${r.status}`);return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();};
 const [bin,...maps]=await Promise.all([fetch(manifest.base+manifest.bin).then(inflate),
  ...manifest.atlases.flatMap(a=>[load(a.natural,true,opts.half),load(a.lamps,true,opts.half),load(a.ao,false,false)])]);
 if(opts.isDisposed()){maps.forEach(t=>t.dispose());return;}
 const baked:Baked={count:0,missed:0,textures:maps};
 const byMaterial=new Map<string,T.MeshStandardMaterial>(),unused=new Set(manifest.meshes);
 for(const mesh of targets){
  const sig=signature(mesh),entry=[...unused].find(e=>same(e.sig,sig));
  if(!entry){baked.missed++;continue;}
  unused.delete(entry);
  const old=mesh.geometry;mesh.geometry=rebuild(old,entry,bin,manifest.uvSteps);old.dispose();
  const source=mesh.material as T.MeshStandardMaterial,key=source.uuid+'|'+entry.atlas;
  let material=byMaterial.get(key);
  if(!material){const a=manifest.atlases[entry.atlas];material=bakedMaterial(source,maps.slice(entry.atlas*3,entry.atlas*3+3),a.range,manifest.gain);byMaterial.set(key,material);}
  mesh.material=material;baked.count++;
 }
 return baked;
}
