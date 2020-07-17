import logging


from kubernetes import client, config

from baremetal.common import jsonobject, utils, http, exceptions
from baremetal.conductor import models
from oslo_config import cfg



logger = logging.getLogger(__name__)
CONF = cfg.CONF

class KubePlugin(object):
    def __init__(self):
        self.api_host = CONF.k8sInfo.host
        self.image_registry = CONF.k8sInfo.image_registry
        self.api_token = CONF.k8sInfo.token
        self.aConfiguration = client.Configuration()
        self.aConfiguration.host = self.api_host
        self.aConfiguration.verify_ssl = False
        self.aConfiguration.debug = True
        self.aConfiguration.api_key = {"authorization": "Bearer " + self.api_token}
        self.aApiClient = client.ApiClient(self.aConfiguration)

    @utils.replyerror
    def create_multus(self, req):
        _api = client.CustomObjectsApi(self.aApiClient)
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("create k8 customer monitor multus:%s" % req[http.REQUEST_BODY])
        _node, _physical_iface, _vlan_id, _ipaddr  = body.node, body.physical_iface, body.vlan_id, body.ipaddr
        _maskprefix = utils.exchange_mask(body.maskaddr)
        _cidr = utils.exchange_cidr(_ipaddr, _maskprefix)
        _multus_name = "{node}-{iface}-{vlan}".format(node=_node, iface=_physical_iface, vlan=_vlan_id)
        _net_range = """{{
                    "cniVersion": "0.3.0",
                    "type": "macvlan",
                    "master": "{iface}.{vlan}",
                    "mode": "bridge",
                    "ipam": {{
                        "type": "host-local",
                        "subnet": "{cidr}",
                        "rangeStart": "{ip_start}",
                        "rangeEnd": "{ip_end}",
                        "routes": [
                            {{"dst": "0.0.0.0/0"}}
                        ],
                        "gateway": ""
                    }}
                }}""".format(iface=_physical_iface, vlan=_vlan_id, cidr=_cidr, ip_start=_ipaddr, ip_end=_ipaddr)
        _net_config = {
            "apiVersion": "k8s.cni.cncf.io/v1",
            "kind": "NetworkAttachmentDefinition",
            "metadata": {"name": _multus_name},
            "spec": {
                "config": _net_range
            }
        }
        try:
            thread = _api.create_namespaced_custom_object(
                group="k8s.cni.cncf.io",
                version="v1",
                namespace="default",
                plural="network-attachment-definitions",
                body=_net_config,
                async_req=True
            )
            logger.debug("create multus success: %s", thread.get())
        except Exception as e:
            logger.error("create multus failed: %s", e)
            raise exceptions.CreateMultusError(name=_multus_name, error=str(e))
        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)


    @utils.replyerror
    def delete_multus(self, req):
        _api = client.CustomObjectsApi(self.aApiClient)
        body = jsonobject.loads(req[http.REQUEST_BODY])
        logger.debug("delete k8 customer monitor network:%s" % req[http.REQUEST_BODY])
        _node, _physical_iface, _vlan_id = body.node, body.physical_iface, body.vlan_id
        _multus_name = "{node}-{iface}-{vlan}".format(node=_node, iface=_physical_iface, vlan=_vlan_id)
        try:
            thread = _api.delete_namespaced_custom_object(
                group="k8s.cni.cncf.io",
                version="v1",
                name=_multus_name,
                namespace="default",
                plural="network-attachment-definitions",
                body=client.V1DeleteOptions(),
                async_req=True
            )
            logger.debug("delete multus success: %s", thread.get())
        except Exception as e:
            logger.error("delete multus failed: %s", e)
            raise exceptions.DeleteMultusError(name=_multus_name, error=str(e))
        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)

    @utils.replyerror
    def create_deployment(self, req):
        _api = client.AppsV1Api(self.aApiClient)
        body = jsonobject.loads(req[http.REQUEST_BODY])
        _node, _vlan_id, _con_ip, _physical_iface = body.node, body.vlan_id, body.con_ip, body.physical_iface
        _deployment_name = "{node}-{vlan}".format(node=_node, vlan=_vlan_id)
        _multus_name = "{node}-{iface}-{vlan}".format(node=_node, iface=_physical_iface, vlan=_vlan_id)
        logger.debug("create k8 monitor deployment:%s" % req[http.REQUEST_BODY])
        dep_config = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {
                "name": _deployment_name
            },
            "spec": {
                "replicas": 1,
                "selector": {
                    "matchLabels": {
                        "bmsnode": _node
                    }
                },
                "template": {
                    "metadata": {
                        "labels": {
                            "bmsnode": _node
                        },
                        "annotations": {
                            "k8s.v1.cni.cncf.io/networks": _multus_name
                        }
                    },
                    "spec": {
                        "containers": [
                            {
                                "name": _deployment_name,
                                "image": self.image_registry,
                                "env": [
                                    {
                                        "name": "vlan_id",
                                        "value": _vlan_id
                                    },
                                    {
                                        "name": "control_ip",
                                        "value": _con_ip
                                    }
                                ],
                                "ports": [
                                    {
                                        "name": "prometheus",
                                        "containerPort": 9090
                                    },
                                    {
                                        "name": "op",
                                        "containerPort": 9999
                                    }
                                ]
                            }
                        ],
                        "nodeSelector": {
                            "bmsnode": _node
                        }
                    }
                }
            }
        }
        try:
            thread = _api.create_namespaced_deployment(
                namespace="default",
                body=dep_config,
                async_req=True
            )
            logger.debug("create monitor deployment success: %s", thread.get())
        except Exception as e:
            logger.error("create monitor deployment failed: %s", e)
            raise exceptions.Createdeployment(name=_deployment_name, error=str(e))
        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)


    @utils.replyerror
    def delete_deployment(self, req):
        _api = client.AppsV1Api(self.aApiClient)
        body = jsonobject.loads(req[http.REQUEST_BODY])
        _node, _vlan_id, _con_ip, _physical_iface = body.node, body.vlan_id, body.con_ip, body.physical_iface
        _deployment_name = "{node}-{vlan}".format(node=_node, vlan=_vlan_id)
        try:
            thread = _api.delete_namespaced_deployment(
                name=_deployment_name,
                namespace="default",
                async_req=True
            )
            logger.debug("delete monitor deployment success: %s", thread.get())
        except Exception as e:
            logger.error("delete monitor deployment failed: %s", e)
            raise exceptions.Deletedeployment(name=_deployment_name, error=str(e))
        rsp = models.AgentResponse()
        return jsonobject.dumps(rsp)




















