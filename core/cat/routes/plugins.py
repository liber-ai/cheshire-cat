import mimetypes
import tempfile
from typing import Dict
import shutil
from fastapi import Request, APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from cat.log import log


router = APIRouter()


# GET plugins
@router.get("/", status_code=200)
async def list_available_plugins(request: Request) -> Dict:
    """List available plugins"""

    # access cat instance
    ccat = request.app.state.ccat

    # plugins are managed by the MadHatter class a = b if b else val
    plugins = ccat.mad_hatter.plugins or []

    # retrieve plugins from official repo
    registry = []

    return {
        "status": "success", 
        "results": len(plugins) + len(registry), 
        "installed": plugins,
        "registry": registry
    }


@router.post("/upload/")
async def upload_plugin(
    request: Request,
    file: UploadFile
) -> Dict:
    """Install a new plugin from a zip file"""

    # access cat instance
    ccat = request.app.state.ccat

    # check if this is a zip file
    content_type = mimetypes.guess_type(file.filename)[0]
    log(f"Uploading {content_type} plugin {file.filename}", "INFO")
    if content_type != "application/zip":
        return JSONResponse(
            status_code=422,
            content={
                "error": f'MIME type `{file.content_type}` not supported. Please upload `application/zip` (a .zip file).'
            },
        )
    
    # Create temporary file (dunno how to extract from memory) #TODO: extract directly from memory
    file_bytes = file.file.read()
    temp_file = tempfile.NamedTemporaryFile(dir="/tmp/", delete=False)
    temp_name = temp_file.name
    with open(temp_name, "wb") as temp_binary_file:
        # Write bytes to file
        temp_binary_file.write(file_bytes)

    # Extract into plugins folder
    shutil.unpack_archive(temp_name, ccat.get_plugin_path(), "zip")

    # align plugins (update db and embed new tools)
    ccat.bootstrap()

    plugins = ccat.mad_hatter.plugins
    ## TODO: get the plugin_id from the extracted folder, not the name of the zipped file
    found = [plugin for plugin in plugins if plugin["id"] == file.filename.replace('.zip', '')]

    log(f"Successfully uploaded {found[0]['id']} plugin", "INFO")

    # reply to client
    return {
        "filename": file.filename,
        "content-type": file.content_type,
        "info": found[0]
    }


@router.put("/toggle/{plugin_id}", status_code=200)
async def toggle_plugin(plugin_id: str, request: Request) -> Dict:
    """Enable or disable a single plugin"""

    # access cat instance
    ccat = request.app.state.ccat

    return {"error": "to be implemented"}


@router.get("/{plugin_id}", status_code=200)
async def get_plugin_details(plugin_id: str, request: Request) -> Dict:
    """Returns information on a single plugin"""

    # access cat instance
    ccat = request.app.state.ccat

    # plugins are managed by the MadHatter class
    plugins = ccat.mad_hatter.plugins
    # there should be only one plugin with that id
    found = [plugin for plugin in plugins if plugin["id"] == plugin_id]

    if not found:
        raise HTTPException(status_code=404, detail="Item not found")

    return {
        "status": "success", 
        "data": found[0]
    }


@router.delete("/{plugin_id}", status_code=200)
async def delete_plugin(plugin_id: str, request: Request) -> Dict:
    """Physically remove plugin."""

    # access cat instance
    ccat = request.app.state.ccat

    plugins = ccat.mad_hatter.plugins
    found = [plugin for plugin in plugins if plugin["id"] == plugin_id]

    if not found:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # remove plugin folder
    shutil.rmtree(ccat.get_plugin_path() + plugin_id)

    # align plugins (update db and embed new tools)
    ccat.bootstrap()

    return {
        "status": "success", 
        "deleted": plugin_id
    }