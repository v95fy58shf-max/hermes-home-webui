import Router from '@koa/router'
import * as ctrl from '../../controllers/hermes/memory'

export const memoryRoutes = new Router()

memoryRoutes.get('/api/hermes/memory', ctrl.get)
memoryRoutes.post('/api/hermes/memory', ctrl.save)
memoryRoutes.get('/api/hermes/family-logs', ctrl.listFamilyLogs)
memoryRoutes.post('/api/hermes/family-logs', ctrl.addFamilyLog)
memoryRoutes.put('/api/hermes/family-logs/:id', ctrl.updateFamilyLog)
memoryRoutes.delete('/api/hermes/family-logs/:id', ctrl.deleteFamilyLog)
