from pathlib import Path
from test_browser_components import browser_page


def test_offline_checkpoint_survives_reopen_and_failed_sync(browser_page):
    page=browser_page
    page.route('http://localhost/**',lambda route:route.fulfill(body='<html><body>Offline storage test</body></html>',content_type='text/html'))
    page.goto('http://localhost/')
    source=(Path(__file__).resolve().parents[1]/'mobile/offline-store.js').read_text(encoding='utf8')
    source=source.replace('export class OfflineStore','class OfflineStore').replace('export function syncTransport','function syncTransport')
    page.add_script_tag(type='module',content=source+';window.OfflineStore=OfflineStore;')
    page.context.set_offline(True)
    result=page.evaluate("""async()=>{
      let store=await OfflineStore.open('first');
      await store.save({pgn:'1. e4 *',ply:1},{kind:'move'});
      await store.save({pgn:'1. e4 e5 *',ply:2},{kind:'move'});
      const device=store.device;store.close();
      store=await OfflineStore.open('first');
      store.transport=async()=>{throw Error('offline');};
      await store.sync().catch(()=>{});
      const saved=await store.current(),pending=await store.pending();
      const other=await OfflineStore.open('other');
      const isolated=await other.current();other.close();store.close();
      return {saved,pending,isolated,sameDevice:device===store.device};
    }""")
    assert result['saved']['checkpoint']['ply']==2
    assert result['saved']['sequence']==2
    assert len(result['pending'])==2 and result['sameDevice']
    assert result['isolated']['checkpoint'] is None
    page.context.set_offline(False)
    result=page.evaluate("""async()=>{
      const store=await OfflineStore.open('first');
      const received=new Map();let loseResponse=true;
      store.transport=async batch=>{
        for(const event of batch.events)received.set(event.id,event);
        if(loseResponse){loseResponse=false;throw Error('response lost');}
        return {acknowledged:Math.max(...[...received.values()].map(e=>e.sequence))};
      };
      await store.sync().catch(()=>{});
      const beforeRetry=(await store.pending()).length;
      await store.sync();
      const result={beforeRetry,unique:received.size,pending:(await store.pending()).length,
        checkpoint:(await store.current()).checkpoint};store.close();return result;
    }""")
    assert result=={'beforeRetry':2,'unique':2,'pending':0,'checkpoint':{'pgn':'1. e4 e5 *','ply':2}}
