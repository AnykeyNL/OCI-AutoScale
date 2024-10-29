import io
import json
import logging
import subprocess

from fdk import response


def handler(ctx, data: io.BytesIO = None):
    result = None
    try:
        logging.getLogger().info("Scaling started")
        result = subprocess.run(["/bin/python", "AutoScaleALL.py", "-rp"], capture_output=True)
        logging.getLogger().info("Scaling completed ")
        logging.getLogger().info("subprocess result out"+ str(result.stdout))
        logging.getLogger().info("subprocess result err"+ str(result.stderr))
        return response.Response(
            ctx, response_data=json.dumps(
                {"message": "Processing complete", "result_out": str(result.stdout), "result_err": str(result.stderr)}),
            headers={"Content-Type": "application/json"}
        )
    except (Exception, ValueError) as ex:
        logging.getLogger().info('error executing AutoScaleALL.py')
        logging.getLogger().error("result.stdout:"+str(result.stdout))
        logging.getLogger().error("result.stderr:"+str(result.stderr))
        logging.getLogger().error(str(ex))

    return response.Response(
        ctx, response_data=json.dumps(
            {"message": "Processing failed"}),
        headers={"Content-Type": "application/json"}
    )