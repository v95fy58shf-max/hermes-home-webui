import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/gateways'

export const gatewayRoutes = new Router()

gatewayRoutes.get('/api/hermes/gateways', ctrl.list)
gatewayRoutes.post('/api/hermes/gateways', ctrl.create)
gatewayRoutes.patch('/api/hermes/gateways/:name/member-name', ctrl.updateMemberName)
gatewayRoutes.post('/api/hermes/gateways/:name/start', ctrl.start)
gatewayRoutes.post('/api/hermes/gateways/:name/stop', ctrl.stop)
gatewayRoutes.get('/api/hermes/gateways/:name/health', ctrl.health)
