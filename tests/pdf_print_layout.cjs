'use strict';
// Chromium streams have a byte length. Binary data may itself end in CR (0x0D),
// which a newline-delimited regex would incorrectly remove from the checksum.
const assert=require('node:assert/strict');
const zlib=require('node:zlib');
function printedTextLayout(pdf){
  const layout=[],raw=pdf.toString('latin1');
  const objects=/(?:^|[\r\n])\d+\s+\d+\s+obj\s*(<<[\s\S]*?>>)\s*stream\r?\n/g;
  for(const match of raw.matchAll(objects)){
    const header=match[1],length=/\/Length\s+(\d+)\b(?!\s+\d+\s+R)/.exec(header);
    assert.ok(length,'Chromium print stream must declare its direct byte length');
    const start=match.index+match[0].length,end=start+Number(length[1]);
    assert.ok(end<=pdf.length&&/^\r?\nendstream\b/.test(raw.slice(end)),
      'Printed PDF stream must have exactly its declared length');
    const flate=header.includes('/FlateDecode');
    if(header.includes('/Filter')&&!flate)continue; // Images are not text drawing operators.
    const bytes=pdf.subarray(start,end);
    const stream=(flate?zlib.inflateSync(bytes):bytes).toString('latin1');
    const text=stream.match(/\bBT\b[\s\S]*?\bET\b/g);
    if(!text)continue;
    const transforms=(stream.match(/(?:-?\d+(?:\.\d+)?\s+){6}cm/g)||[])
      .filter(value=>!/^1 0 0 -1 0 \d+ cm$/.test(value));
    layout.push({text,transforms});
  }
  assert.ok(layout.length,'Printed PDF must contain readable text drawing operators');
  return layout;
}
function selfTest(){
  let compressed,plain;
  for(let byte=0;byte<256;byte++){
    plain=Buffer.concat([Buffer.from('BT\n1 0 0 1 10 20 Tm\n<0041> Tj\nET\n%'),Buffer.from([byte]),Buffer.from('\n')]);
    compressed=zlib.deflateSync(plain);
    if(compressed.at(-1)===13)break;
  }
  assert.equal(compressed.at(-1),13,'Fixture exercises a real compressed checksum ending in CR');
  const pdf=(content,filter='',newline='\n')=>Buffer.concat([
    Buffer.from(`%PDF-1.4\n1 0 obj\n<< /Length ${content.length} ${filter} >>\nstream\n`),
    content,Buffer.from(newline+'endstream\nendobj\n%%EOF')]);
  const reference=printedTextLayout(pdf(plain));
  for(const newline of ['\n','\r\n'])assert.deepEqual(printedTextLayout(pdf(compressed,'/Filter /FlateDecode',newline)),reference);
  assert.throws(()=>printedTextLayout(pdf(compressed.subarray(0,-1),'/Filter /FlateDecode')));
  assert.throws(()=>printedTextLayout(Buffer.from('%PDF-1.4\n%%EOF')));
}
module.exports=printedTextLayout;
module.exports.selfTest=selfTest;
if(require.main===module){selfTest();console.log('PASS PDF: longitud binaria exacta, checksum final CR, LF/CRLF, texto sin comprimir y rechazo de truncado/vacío.');}
